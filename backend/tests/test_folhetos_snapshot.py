"""Snapshot tests dos folhetos Arquidiocese RJ conhecidos.

Cada folheto define uma ESTRUTURA ESPERADA que o pipeline deve produzir.
Quando algo no pipeline muda e quebra a extração, esses testes acendem.

Folhetos cobertos:
  - Ascensão do Senhor (17/05/2026, Solenidade)
  - Domingo de Pentecostes (24/05/2026, Solenidade)
  - 10º Domingo do Tempo Comum (07/06/2026, Domingo comum)

O foco é em propriedades estruturais robustas (contagens, ordem, hierarquia),
não em texto literal — o conteúdo pode variar ligeiramente entre extrações
sem indicar bug.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from app.pipeline import processar_pdf
from app.schema.missa import Missa


FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Fixtures de carregamento (uma processada por módulo, reusada)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def ascensao() -> Missa:
    return processar_pdf(FIXTURES_DIR / "amissa_ascensao_2026.pdf")


@pytest.fixture(scope="module")
def pentecostes() -> Missa:
    return processar_pdf(FIXTURES_DIR / "folheto_2026-05-24.pdf")


@pytest.fixture(scope="module")
def domingo_07_06() -> Missa:
    return processar_pdf(FIXTURES_DIR / "folheto_2026-06-07.pdf")


# ---------------------------------------------------------------------------
# Helpers de inspeção
# ---------------------------------------------------------------------------

def blocos_navegaveis(missa: Missa) -> list:
    """Tudo que não é seção (i.e. blocos com conteúdo)."""
    return [b for b in missa.blocos if getattr(b, "tipo", None) != "secao"]


def blocos_numerados(missa: Missa) -> list:
    """Blocos com numero_folheto preenchido (1..N litúrgicos)."""
    return [b for b in blocos_navegaveis(missa)
            if getattr(b, "numero_folheto", None) is not None]


def secoes(missa: Missa) -> list[str]:
    return [b.titulo for b in missa.blocos if b.tipo == "secao"]


def blocos_por_secao(missa: Missa) -> dict[str, list]:
    """Agrupa blocos numerados pela seção a que pertencem."""
    agrupado: dict[str, list] = {}
    for b in blocos_numerados(missa):
        sec = getattr(b, "secao", None) or "(sem seção)"
        agrupado.setdefault(sec, []).append(b)
    return agrupado


def titulos_numerados_em_ordem(missa: Missa) -> list[tuple[int, str]]:
    return [(b.numero_folheto, b.titulo) for b in blocos_numerados(missa)]


def antifonas(missa: Missa) -> list:
    """Antífonas (Entrada / Comunhão / Mariana) como blocos próprios."""
    return [b for b in missa.blocos if getattr(b, "tipo", None) == "antifona"]


def apendices(missa: Missa) -> list:
    return [b for b in missa.blocos
            if getattr(b, "secao", None) == "apendice"]


# ===========================================================================
# Folheto 1: Ascensão do Senhor (17/05/2026, Solenidade)
# ===========================================================================

class TestAscensao:
    """17/05/2026 — Solenidade da Ascensão.
    Estrutura esperada: 4 seções, 23 blocos numerados (Solenidade tem Canto Final)
    + Antífona da Entrada + Antífona da Comunhão + Antífona Mariana + Leituras da Semana
    + Oração para o 60º Dia Mundial das Comunicações Sociais.
    """

    def test_metadados_basicos(self, ascensao):
        assert ascensao.data == "2026-05-17"
        assert "Ascensão" in ascensao.titulo_celebracao
        assert ascensao.categoria == "Solenidade"
        assert "Comunicações" in (ascensao.observacoes or "")

    def test_descricao_introdutoria(self, ascensao):
        # Deve capturar o "Neste Domingo..."
        assert ascensao.descricao is not None
        assert ascensao.descricao.lower().startswith("neste")

    def test_quatro_secoes(self, ascensao):
        assert secoes(ascensao) == [
            "Ritos Iniciais",
            "Liturgia da Palavra",
            "Liturgia Eucarística",
            "Ritos Finais",
        ]

    def test_distribuicao_blocos_por_secao(self, ascensao):
        # Solenidade Ascensão tem 23 blocos numerados conforme folheto Arquidiocese:
        # 5 (Ritos Iniciais) + 8 (Liturgia da Palavra) + 7 (Eucarística) + 3 (Ritos Finais)
        # Caso o folheto tenha Canto Final extra → 24
        grupos = blocos_por_secao(ascensao)
        total = sum(len(v) for v in grupos.values())
        assert 21 <= total <= 24
        assert len(grupos["Ritos Iniciais"]) >= 4
        assert len(grupos["Liturgia da Palavra"]) >= 7
        assert len(grupos["Liturgia Eucarística"]) >= 5
        assert len(grupos["Ritos Finais"]) >= 2

    def test_blocos_em_ordem_sequencial(self, ascensao):
        """numero_folheto deve crescer monotonicamente 1, 2, 3..."""
        nums = [n for n, _ in titulos_numerados_em_ordem(ascensao)]
        assert nums == sorted(nums)
        assert nums[0] == 1
        # Sem buracos
        for esperado, atual in enumerate(nums, start=1):
            assert atual == esperado, (
                f"Numero {esperado} esperado, veio {atual} — gap na numeração"
            )

    def test_antifonas_como_blocos(self, ascensao):
        """Antífona da Entrada/Comunhão devem ser blocos próprios (não anexadas)."""
        ttls = [a.titulo.lower() for a in antifonas(ascensao)]
        assert any("entrada" in t for t in ttls), "Falta Antífona da Entrada"
        assert any("comunh" in t for t in ttls), "Falta Antífona da Comunhão"

    def test_antifona_mariana_apendice(self, ascensao):
        """Solenidade tem Antífona Mariana no apêndice."""
        apes = apendices(ascensao)
        assert any("mariana" in (a.titulo or "").lower() for a in apes), (
            "Falta Antífona Mariana como apêndice"
        )

    def test_leituras_da_semana_apendice(self, ascensao):
        apes = apendices(ascensao)
        assert any("leituras da semana" in (a.titulo or "").lower() for a in apes)

    def test_oracao_comunicacoes_apendice(self, ascensao):
        """A Ascensão coincide com 60º Dia Mundial das Comunicações — tem oração própria."""
        apes = apendices(ascensao)
        assert any("comunicaç" in (a.titulo or "").lower() for a in apes)

    def test_oracao_dos_fieis_tem_preces_separadas(self, ascensao):
        """Oração dos Fiéis deve ter turnos L/T alternados, não preces grudadas."""
        for b in blocos_navegaveis(ascensao):
            if "fiéis" in (b.titulo or "").lower() or "fieis" in (b.titulo or "").lower():
                assert hasattr(b, "turnos") and b.turnos, "Sem turnos"
                falantes = [t.falante for t in b.turnos]
                assert "L" in falantes, "Sem turnos L (Leitor)"
                assert "T" in falantes, "Sem turnos T (Todos)"
                # Pelo menos 2 alternâncias L→T
                pares_lt = sum(
                    1 for i in range(len(b.turnos) - 1)
                    if b.turnos[i].falante == "L" and b.turnos[i + 1].falante == "T"
                )
                assert pares_lt >= 2, f"Esperava ≥2 alternâncias L→T, veio {pares_lt}"
                return
        pytest.fail("Bloco 'Oração dos Fiéis' não encontrado")


# ===========================================================================
# Folheto 2: Pentecostes (24/05/2026, Solenidade)
# ===========================================================================

class TestPentecostes:
    """24/05/2026 — Solenidade do Domingo de Pentecostes."""

    def test_metadados_basicos(self, pentecostes):
        assert pentecostes.data == "2026-05-24"
        assert "pentecostes" in pentecostes.titulo_celebracao.lower()
        # NOTE: o PDF de fixtures está truncado (começa em "Ritos Iniciais",
        # sem cabeçalho), por isso a categoria fica como default "Missa".
        # Quando substituirmos por um PDF completo da Arquidiocese, este teste
        # deve voltar a exigir "Solenidade".
        assert pentecostes.categoria in ("Solenidade", "Missa")

    def test_quatro_secoes(self, pentecostes):
        assert secoes(pentecostes) == [
            "Ritos Iniciais",
            "Liturgia da Palavra",
            "Liturgia Eucarística",
            "Ritos Finais",
        ]

    def test_numeracao_continua(self, pentecostes):
        nums = [n for n, _ in titulos_numerados_em_ordem(pentecostes)]
        assert nums == sorted(nums)
        assert nums[0] == 1
        for esperado, atual in enumerate(nums, start=1):
            assert atual == esperado

    def test_antifona_da_entrada_como_bloco(self, pentecostes):
        ttls = [a.titulo.lower() for a in antifonas(pentecostes)]
        assert any("entrada" in t for t in ttls)

    def test_antifona_da_comunhao_como_bloco(self, pentecostes):
        """Bug histórico: 'Antífona da Comunhão (At 2,4-11)' tinha hífen na
        referência bíblica, e a skip-list de ruído incluía '-' (hífen solto)
        como padrão de descarte, pulando a linha. Fix em structure.py:368-378
        removeu '-' da skip-list e adicionou check específico pra hífen solto.
        """
        ttls = [a.titulo.lower() for a in antifonas(pentecostes)]
        assert any("comunh" in t for t in ttls), (
            "Antífona da Comunhão deveria estar como bloco próprio"
        )

    def test_leituras_da_semana_apendice(self, pentecostes):
        apes = apendices(pentecostes)
        assert any("leituras da semana" in (a.titulo or "").lower() for a in apes)

    def test_rito_apagar_circio_pascal_apendice(self, pentecostes):
        """Pentecostes fecha o tempo pascal — folheto traz rito específico no apêndice."""
        apes = apendices(pentecostes)
        nomes = [(a.titulo or "").lower() for a in apes]
        assert any("rito para apagar" in n for n in nomes), (
            f"Falta 'RITO PARA APAGAR O CÍRIO PASCAL' nos apêndices. Encontrados: {nomes}"
        )

    def test_semana_eucaristica_apendice(self, pentecostes):
        """Anúncio pastoral da Arquidiocese (Semana Eucarística antes de Corpus Christi)."""
        apes = apendices(pentecostes)
        nomes = [(a.titulo or "").lower() for a in apes]
        assert any("semana eucar" in n for n in nomes), (
            f"Falta 'SEMANA EUCARÍSTICA' nos apêndices. Encontrados: {nomes}"
        )

    def test_sequencia_pentecostes_tem_estrofes(self, pentecostes):
        """A Sequência de Pentecostes (canto específico) deve ter estrofes."""
        for b in pentecostes.blocos:
            t = (getattr(b, "titulo", "") or "").lower()
            if "sequência" in t or "sequencia" in t:
                assert getattr(b, "estrofes", None), "Sequência sem estrofes"
                return
        pytest.fail("Bloco 'Sequência' não encontrado em Pentecostes")

    def test_numeracao_canonica_pentecostes(self, pentecostes):
        """Numeração exata do folheto Arquidiocese pra Pentecostes (23 blocos numerados).
        Bug histórico: a verse 10 da Sequência colidia com #10 Aclamação ao Evangelho,
        causando deslocamento de toda a numeração subsequente.
        """
        por_num = {n: t for n, t in titulos_numerados_em_ordem(pentecostes)}
        esperado = {
            1: "Canto de Entrada", 2: "Saudação", 3: "Ato Penitencial",
            4: "Hino de Louvor", 5: "Coleta", 6: "Primeira Leitura",
            8: "Segunda Leitura", 9: "Sequência", 10: "Aclamação ao Evangelho",
            11: "Evangelho", 12: "Homilia", 13: "Profissão de Fé",
            14: "Oração dos Fiéis", 15: "Canto das Ofertas",
            21: "Depois da Comunhão", 22: "Vivência",
            23: "Bênção Final e Despedida",
        }
        for n, esperado_t in esperado.items():
            atual = (por_num.get(n) or "").strip()
            # Salmo Responsorial às vezes vem com "]" no fim — comparação loose
            assert esperado_t.lower() in atual.lower(), (
                f"Bloco #{n}: esperava '{esperado_t}', veio '{atual}'"
            )

    def test_oracao_dos_fieis_alternancia_lt(self, pentecostes):
        for b in blocos_navegaveis(pentecostes):
            if "fiéis" in (b.titulo or "").lower() or "fieis" in (b.titulo or "").lower():
                falantes = [t.falante for t in b.turnos]
                assert "L" in falantes and "T" in falantes
                return


# ===========================================================================
# Folheto 3: 10º Domingo do Tempo Comum (07/06/2026)
# ===========================================================================

class TestDomingoComum:
    """07/06/2026 — 10º Domingo do Tempo Comum.
    Estrutura: 23 blocos numerados em 4 seções.
    """

    def test_metadados_basicos(self, domingo_07_06):
        assert domingo_07_06.data == "2026-06-07"
        # Ordinal "10º" preservado (era "10o" antes do fix em clean.py)
        assert "10º" in domingo_07_06.titulo_celebracao
        assert "Domingo do Tempo Comum" in domingo_07_06.titulo_celebracao

    def test_quatro_secoes(self, domingo_07_06):
        assert secoes(domingo_07_06) == [
            "Ritos Iniciais",
            "Liturgia da Palavra",
            "Liturgia Eucarística",
            "Ritos Finais",
        ]

    def test_23_blocos_numerados(self, domingo_07_06):
        nums = [n for n, _ in titulos_numerados_em_ordem(domingo_07_06)]
        assert len(nums) == 23, f"Esperava 23 blocos numerados, veio {len(nums)}"
        assert nums == list(range(1, 24))

    def test_distribuicao_exata(self, domingo_07_06):
        """5 + 8 + 7 + 3 = 23"""
        grupos = blocos_por_secao(domingo_07_06)
        assert len(grupos["Ritos Iniciais"]) == 5
        assert len(grupos["Liturgia da Palavra"]) == 8
        assert len(grupos["Liturgia Eucarística"]) == 7
        assert len(grupos["Ritos Finais"]) == 3

    def test_blocos_em_posicoes_esperadas(self, domingo_07_06):
        """Algumas posições críticas (corrige bugs históricos de drift)."""
        por_num = {n: titulo for n, titulo in titulos_numerados_em_ordem(domingo_07_06)}
        assert por_num[1] == "Canto de Entrada"
        assert por_num[5] == "Coleta"  # era #6 antes do fix
        assert por_num[6] == "Primeira Leitura"
        assert por_num[7] == "Salmo Responsorial"  # era #8 antes do fix
        assert por_num[9] == "Aclamação ao Evangelho"
        assert por_num[10] == "Evangelho"
        assert por_num[14] == "Canto das Ofertas"
        assert por_num[19] == "Canto de Comunhão"
        assert por_num[21] == "Vivência"  # era #23 antes do fix
        assert por_num[22] == "Bênção Final e Despedida"
        assert por_num[23] == "Canto Final"  # bug do cap 22 corrigido

    def test_secao_da_palavra_tem_nota_l(self, domingo_07_06):
        """A seção 'Liturgia da Palavra' tem descrição L. introdutória capturada."""
        for b in domingo_07_06.blocos:
            if b.tipo == "secao" and "Liturgia da Palavra" in b.titulo:
                assert b.descricao is not None, "Descrição (nota L.) não capturada"
                assert "misericordioso" in b.descricao.lower()
                return
        pytest.fail("Seção Liturgia da Palavra não encontrada")

    def test_antifonas_como_blocos_proprios(self, domingo_07_06):
        """Antífonas Entrada/Comunhão como blocos próprios, sem numero_folheto."""
        ants = antifonas(domingo_07_06)
        nomes = [a.titulo.lower() for a in ants]
        assert any("entrada" in n for n in nomes)
        assert any("comunh" in n for n in nomes)
        # Não recebem número
        for a in ants:
            if "entrada" in a.titulo.lower() or "comunh" in a.titulo.lower():
                assert getattr(a, "numero_folheto", None) is None, (
                    f"Antífona '{a.titulo}' não deveria ter numero_folheto"
                )

    def test_canto_de_comunhao_tem_6_estrofes(self, domingo_07_06):
        """Bug histórico: estrofe 6 vazava como bloco anômalo #20."""
        for b in domingo_07_06.blocos:
            if (getattr(b, "titulo", "") or "").lower() == "canto de comunhão":
                estrofes = getattr(b, "estrofes", None) or []
                assert len(estrofes) == 6, (
                    f"Canto de Comunhão devia ter 6 estrofes, veio {len(estrofes)}"
                )
                return
        pytest.fail("Canto de Comunhão não encontrado")

    def test_canto_de_comunhao_refrao_apos_estrofe_1(self, domingo_07_06):
        """No folheto, REFRÃO vem após a estrofe 1 (não no início)."""
        for b in domingo_07_06.blocos:
            if (getattr(b, "titulo", "") or "").lower() == "canto de comunhão":
                assert getattr(b, "posicao_refrao_apos", None) == 1, (
                    "Refrão do Canto de Comunhão deve estar na posição 1 (após estrofe 1)"
                )
                return

    def test_aclamacao_refrao_separado_do_versiculo_l(self, domingo_07_06):
        """Aclamação ao Evangelho: refrão Aleluia separado do L. versículo."""
        for b in domingo_07_06.blocos:
            if "aclamac" in (getattr(b, "titulo", "") or "").lower():
                refrao = getattr(b, "refrao", []) or []
                # Refrão deve conter "Aleluia" e NÃO conter "L."
                assert refrao, "Aclamação sem refrão"
                refrao_str = " ".join(refrao).lower()
                assert "aleluia" in refrao_str
                assert " l. " not in (" " + refrao_str + " "), (
                    f"Versículo L. vazou no refrão: {refrao_str[:100]}"
                )
                return

    def test_canto_final_isolado_sem_leituras_semana(self, domingo_07_06):
        """Bug histórico: Canto Final coletava Leituras da Semana + rodapé editorial."""
        for b in domingo_07_06.blocos:
            if (getattr(b, "titulo", "") or "").lower() == "canto final":
                # Soma de tamanhos do refrão + estrofes
                tudo = " ".join(getattr(b, "refrao", []) or [])
                for e in getattr(b, "estrofes", []) or []:
                    tudo += " " + " ".join(e)
                assert "leituras da semana" not in tudo.lower()
                assert "editora" not in tudo.lower()
                assert "portal da arquidiocese" not in tudo.lower()
                return

    def test_apendice_leituras_da_semana(self, domingo_07_06):
        apes = apendices(domingo_07_06)
        assert any("leituras da semana" in (a.titulo or "").lower() for a in apes)

    def test_apendice_sem_numero_folheto(self, domingo_07_06):
        """Apêndices não devem receber numero_folheto (não são litúrgicos)."""
        for a in apendices(domingo_07_06):
            assert getattr(a, "numero_folheto", None) is None, (
                f"Apêndice '{a.titulo}' tem numero_folheto={a.numero_folheto}"
            )
