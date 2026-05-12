import json
import re
from pathlib import Path

import pytest

from app.schema.missa import Missa

PDF_FIXTURE = Path(__file__).parent / "fixtures" / "amissa_ascensao_2026.pdf"
JSON_GABARITO = Path(__file__).parent / "fixtures" / "amissa_ascensao_2026.expected.json"


@pytest.fixture(scope="module")
def missa() -> Missa:
    from app.pipeline import processar_pdf
    return processar_pdf(PDF_FIXTURE)


@pytest.fixture(scope="module")
def gabarito() -> dict:
    return json.loads(JSON_GABARITO.read_text(encoding="utf-8"))


class TestMetadados:
    def test_data(self, missa):
        assert missa.data == "2026-05-17"

    def test_titulo(self, missa):
        assert missa.titulo_celebracao == "Ascensão do Senhor"

    def test_categoria(self, missa):
        assert missa.categoria == "Solenidade"

    def test_ano_liturgico(self, missa):
        assert missa.ano_liturgico == "A"

    def test_observacoes_mencionam_dia_das_comunicacoes(self, missa):
        assert "Comunicações Sociais" in (missa.observacoes or "")


class TestCreditos:
    def test_entrada(self, missa):
        assert missa.creditos_cantos.entrada == "José Alves"

    def test_ofertas(self, missa):
        assert missa.creditos_cantos.ofertas == "D.R."

    def test_comunhao(self, missa):
        assert missa.creditos_cantos.comunhao == "Pe. José Weber"

    def test_final(self, missa):
        assert missa.creditos_cantos.final == "Antífona Mariana / Liturgia das Horas"


class TestCantoEntrada:
    @pytest.fixture
    def canto(self, missa):
        return next(b for b in missa.blocos if b.titulo == "Canto de Entrada")

    def test_tipo(self, canto):
        assert canto.tipo == "canto"

    def test_postura(self, canto):
        assert canto.postura == "de_pe"

    def test_refrao_exato(self, canto):
        assert canto.refrao == [
            "O Senhor foi preparar",
            "um lugar para nós no céu.",
        ]

    def test_quantidade_estrofes(self, canto):
        assert len(canto.estrofes) == 4

    def test_primeira_estrofe_exata(self, canto):
        assert canto.estrofes[0] == [
            "Ó varões galileus, que estais no céu a olhar? Aleluia!",
            "O Jesus que subiu ao céu deve, depois voltar! Aleluia!",
        ]

    def test_quarta_estrofe_exata(self, canto):
        assert canto.estrofes[3] == [
            "Ó Jesus, nosso Rei e Senhor, que subis para o céu! Aleluia!",
            "Não deixeis os cristãos a sós: dai-nos o dom de Deus! Aleluia!",
        ]

    def test_nenhum_verso_contem_barra(self, canto):
        for estrofe in canto.estrofes:
            for verso in estrofe:
                assert "/" not in verso

    def test_nenhum_verso_contem_numero_estrofe(self, canto):
        for estrofe in canto.estrofes:
            for verso in estrofe:
                assert not re.match(r"^\d+\.\s", verso)

    def test_creditos_nao_estao_no_canto(self, canto):
        textos = canto.refrao + [v for e in canto.estrofes for v in e]
        for t in textos:
            assert "Entrada:" not in t
            assert "José Alves" not in t


class TestSaudacao:
    @pytest.fixture
    def saudacao(self, missa):
        return next(b for b in missa.blocos if b.titulo == "Saudação")

    def test_tipo(self, saudacao):
        assert saudacao.tipo == "dialogo"

    def test_quatro_turnos(self, saudacao):
        assert len(saudacao.turnos) == 4

    def test_sequencia_falantes(self, saudacao):
        assert [t.falante for t in saudacao.turnos] == ["P", "T", "P", "T"]

    def test_primeiro_turno(self, saudacao):
        assert saudacao.turnos[0].texto == "Em nome do Pai e do Filho e do Espírito Santo."

    def test_segundo_turno(self, saudacao):
        assert saudacao.turnos[1].texto == "Amém."

    def test_terceiro_turno_completo(self, saudacao):
        assert saudacao.turnos[2].texto == \
            "A graça e a paz daquele que é, que era e que vem, estejam convosco."

    def test_quarto_turno(self, saudacao):
        assert saudacao.turnos[3].texto == \
            "Bendito seja Deus, que nos reuniu no amor de Cristo."

    def test_nenhum_turno_orfao(self, saudacao):
        for turno in saudacao.turnos:
            assert turno.texto.strip() != ""

    def test_nenhum_turno_tem_sigla_no_texto(self, saudacao):
        for turno in saudacao.turnos:
            assert not re.match(r"^[PTLVR]\.", turno.texto)


class TestAntifonaEntrada:
    @pytest.fixture
    def antifona(self, missa):
        return next(b for b in missa.blocos if b.titulo == "Antífona da Entrada")

    def test_tipo(self, antifona):
        assert antifona.tipo == "antifona"

    def test_referencia(self, antifona):
        assert antifona.referencia == "At 1,11"

    def test_texto_completo(self, antifona):
        assert antifona.texto == (
            "Homens da Galileia, por que ficais aqui, parados, olhando para o céu? "
            "Esse Jesus virá do mesmo modo como o vistes partir para o céu, aleluia."
        )

    def test_e_bloco_independente(self, missa):
        for bloco in missa.blocos:
            if bloco.titulo == "Saudação":
                conteudo = str(bloco.model_dump())
                assert "Homens da Galileia" not in conteudo


class TestAtoPenitencial:
    @pytest.fixture
    def ato(self, missa):
        return next(b for b in missa.blocos if b.titulo == "Ato Penitencial")

    def test_tem_rubrica_de_silencio(self, ato):
        rubricas = [t for t in ato.turnos if t.falante == "rubrica"]
        assert len(rubricas) >= 1
        assert "silêncio" in rubricas[0].texto.lower()

    def test_alterna_padre_assembleia(self, ato):
        pos_rubrica = [t for t in ato.turnos if t.falante in ("P", "T")]
        falantes = [t.falante for t in pos_rubrica]
        assert falantes.count("P") >= 4
        assert falantes.count("T") >= 4


class TestPrimeiraLeitura:
    @pytest.fixture
    def leitura(self, missa):
        return next(b for b in missa.blocos
                    if hasattr(b, "categoria") and b.categoria == "primeira_leitura")

    def test_referencia(self, leitura):
        assert leitura.referencia == "At 1,1-11"

    def test_postura(self, leitura):
        assert leitura.postura == "sentado"

    def test_introducao(self, leitura):
        assert "Leitura dos Atos" in (leitura.introducao or "")

    def test_conclusao(self, leitura):
        assert leitura.conclusao == "Palavra do Senhor."

    def test_resposta(self, leitura):
        assert leitura.resposta == "Graças a Deus."

    def test_tem_versiculos_numerados(self, leitura):
        assert len(leitura.versiculos) >= 11
        numeros = [v.numero for v in leitura.versiculos]
        assert 1 in numeros
        assert 11 in numeros


class TestPalavraDoDia:
    def test_vem_do_evangelho_da_ascensao(self, missa):
        assert missa.palavra_do_dia.referencia.startswith("Mt 28")

    def test_nao_e_frase_generica_aleatoria(self, missa):
        assert "pão vivo" not in missa.palavra_do_dia.texto

    def test_tema_central(self, missa):
        assert "convosco" in missa.palavra_do_dia.texto.lower() \
            or "dias" in missa.palavra_do_dia.texto.lower()


class TestInvariantesGlobais:
    def _walk_strings(self, obj, caminho="missa"):
        if isinstance(obj, str):
            yield caminho, obj
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                yield from self._walk_strings(item, f"{caminho}[{i}]")
        elif hasattr(obj, "model_dump"):
            for k, v in obj.model_dump().items():
                yield from self._walk_strings(v, f"{caminho}.{k}")
        elif isinstance(obj, dict):
            for k, v in obj.items():
                yield from self._walk_strings(v, f"{caminho}.{k}")

    def test_zero_barras_separadoras(self, missa):
        for caminho, texto in self._walk_strings(missa):
            if "creditos_cantos" in caminho:
                continue
            assert " / " not in texto, f"{caminho}: {texto!r}"

    def test_zero_markdown(self, missa):
        for caminho, texto in self._walk_strings(missa):
            assert "##" not in texto, f"{caminho}: {texto!r}"
            assert "**" not in texto, f"{caminho}: {texto!r}"

    def test_zero_hifens_orfaos(self, missa):
        for caminho, texto in self._walk_strings(missa):
            assert not re.search(r"\w+-\s*\n", texto), f"{caminho}: {texto!r}"

    def test_zero_palavras_mutiladas(self, missa):
        for caminho, texto in self._walk_strings(missa):
            assert "ífona" not in texto or "Antífona" in texto, f"{caminho}: {texto!r}"

    def test_zero_palavras_coladas(self, missa):
        for caminho, texto in self._walk_strings(missa):
            assert "AleQue" not in texto, f"{caminho}: {texto!r}"
            assert "CantodeEntrada" not in texto, f"{caminho}: {texto!r}"

    def test_zero_postura_como_texto(self, missa):
        for caminho, texto in self._walk_strings(missa):
            assert not re.search(r"\(De pé\)", texto), f"{caminho}: {texto!r}"

    def test_zero_siglas_falante_em_texto_de_dialogo(self, missa):
        for bloco in missa.blocos:
            if hasattr(bloco, 'tipo') and bloco.tipo == "dialogo":
                for turno in bloco.turnos:
                    assert not re.match(r"^[PTLVR]\.", turno.texto), f"{bloco.titulo}: {turno.texto!r}"

    def test_ordem_sequencial(self, missa):
        ordens = [b.ordem for b in missa.blocos]
        assert ordens == sorted(ordens)

    def test_todos_blocos_tem_titulo(self, missa):
        for bloco in missa.blocos:
            assert bloco.titulo.strip() != ""


class TestIdempotencia:
    def test_processar_duas_vezes_produz_mesmo_resultado(self):
        from app.pipeline import processar_pdf
        m1 = processar_pdf(PDF_FIXTURE)
        m2 = processar_pdf(PDF_FIXTURE)
        assert m1.model_dump_json() == m2.model_dump_json()
