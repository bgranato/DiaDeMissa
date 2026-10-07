"""Contratos de segurança do Gauntlet Loop.

Estes testes cobrem o limite central: falha do crítico ou da referência não
pode ser convertida em aprovação implícita.
"""
from __future__ import annotations

import json

import pytest

from app.pipeline import montagem_convergente as loop
from app.schema.missa import Antifona, Canto, Missa, Oracao, Secao


class _MissaMinima:
    def model_dump(self):
        return {"blocos": []}


def test_pdf_para_provedor_remove_apenas_prefixo_branco():
    bruto = b" \r\n\t%PDF-1.5\nconteudo"

    assert loop._pdf_para_provedor(bruto) == b"%PDF-1.5\nconteudo"


def test_pdf_para_provedor_preserva_pdf_valido_e_bytes_desconhecidos():
    assert loop._pdf_para_provedor(b"%PDF-1.5\nconteudo") == b"%PDF-1.5\nconteudo"
    assert loop._pdf_para_provedor(b"\x00%PDF-1.5") == b"\x00%PDF-1.5"


def test_mapa_invalido_bloqueia_o_loop(monkeypatch):
    async def resposta_invalida(*_args, **_kwargs):
        return '{"categoria_ou_tema": "sem blocos"}'

    monkeypatch.setattr(loop, "_gerar", resposta_invalida)

    with pytest.raises(loop.ConferenciaIndisponivel):
        loop.gerar_mapa(b"%PDF-teste")


def test_falha_do_conferente_nao_vira_aprovacao(monkeypatch):
    async def falhar(*_args, **_kwargs):
        raise OSError("provedor indisponível")

    monkeypatch.setattr(loop, "_gerar", falhar)

    with pytest.raises(loop.ConferenciaIndisponivel):
        loop.conferir(b"%PDF-teste", _MissaMinima())


def test_resposta_sem_divergencias_bloqueia_em_vez_de_aprovar(monkeypatch):
    async def resposta_invalida(*_args, **_kwargs):
        return '{"ok": true}'

    monkeypatch.setattr(loop, "_gerar", resposta_invalida)

    with pytest.raises(loop.ConferenciaIndisponivel):
        loop.conferir(b"%PDF-teste", _MissaMinima())


def test_divergencia_liturgica_baixa_nao_e_publicavel(monkeypatch):
    """Nenhuma divergência dentro do escopo litúrgico pode passar pelo gate."""
    missa = _MissaMinima()
    monkeypatch.setattr(loop, "MAX_ITER_CONFERENCIA", 1)
    monkeypatch.setattr(loop, "gerar_mapa", lambda _pdf: {"blocos": []})
    monkeypatch.setattr(loop, "montar_com_mapa", lambda *_args, **_kwargs: missa)
    monkeypatch.setattr(loop, "checar_estrutural_vs_mapa", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(loop, "checar_texto_liturgico_vs_fonte", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(loop, "checar_cobertura_palavra_a_palavra", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        loop,
        "conferir",
        lambda *_args, **_kwargs: [{"severidade": "baixa", "escopo": "conteudo_liturgico"}],
    )
    monkeypatch.setattr(loop, "conferir_celebrante", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(loop, "_corrigir", lambda *_args, **_kwargs: missa)

    _resultado, meta = loop.montar_com_conferencia(
        b"%PDF-teste", "texto", pdf_celebrante=b"%PDF-celebrante"
    )

    assert meta["conferida"] is False
    assert meta["iteracoes"] == 1


def test_palavra_fora_do_pdf_e_divergencia_critica():
    class Bloco:
        def model_dump(self):
            return {"titulo": "Canto", "texto": "palavra-inventada"}

    class MissaComBloco:
        descricao = None
        blocos = [Bloco()]

    divergencias = loop.checar_texto_liturgico_vs_fonte(
        "texto litúrgico autêntico do folheto", MissaComBloco()
    )

    # Duas camadas acusam o mesmo texto inventado: o léxico (palavra ausente) e o
    # literal (texto curto fora do fonte). Ambas críticas — publicação bloqueada.
    assert len(divergencias) >= 1
    assert all(d["severidade"] == "critica" for d in divergencias)
    assert all(d["escopo"] == "conteudo_liturgico" for d in divergencias)


def test_sem_pdf_celebrante_bloqueia_a_publicacao(monkeypatch):
    monkeypatch.setattr(loop, "gerar_mapa", lambda *_args: pytest.fail("não deve montar"))

    with pytest.raises(loop.ConferenciaIndisponivel, match="Celebrante ausente"):
        loop.montar_com_conferencia(b"%PDF-celular", "texto")


def test_divergencia_do_celebrante_nao_e_publicavel(monkeypatch):
    missa = _MissaMinima()
    monkeypatch.setattr(loop, "MAX_ITER_CONFERENCIA", 1)
    monkeypatch.setattr(loop, "gerar_mapa", lambda _pdf: {"blocos": []})
    monkeypatch.setattr(loop, "montar_com_mapa", lambda *_args, **_kwargs: missa)
    monkeypatch.setattr(loop, "checar_estrutural_vs_mapa", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(loop, "checar_texto_liturgico_vs_fonte", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(loop, "checar_cobertura_palavra_a_palavra", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(loop, "conferir", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        loop, "conferir_celebrante",
        lambda *_args, **_kwargs: [{"severidade": "critica", "escopo": "conteudo_liturgico"}],
    )
    monkeypatch.setattr(loop, "_corrigir", lambda *_args, **_kwargs: missa)

    _resultado, meta = loop.montar_com_conferencia(
        b"%PDF-celular", "texto", pdf_celebrante=b"%PDF-celebrante"
    )

    assert meta["conferida"] is False
    assert meta["fontes"] == {"principal": "celular", "secundaria": "celebrante"}


# ---------------------------------------------------------------------------
# Revalidação do estado final (regressão 07/10): o veredito nunca pode vir de
# um check anterior à última correção.
# ---------------------------------------------------------------------------

def _fakes_de_loop(monkeypatch, missa):
    monkeypatch.setattr(loop, "gerar_mapa", lambda _pdf: {"blocos": []})
    monkeypatch.setattr(loop, "montar_com_mapa", lambda *_a, **_k: missa)
    monkeypatch.setattr(loop, "checar_estrutural_vs_mapa", lambda *_a, **_k: [])
    monkeypatch.setattr(loop, "checar_texto_liturgico_vs_fonte", lambda *_a, **_k: [])
    monkeypatch.setattr(loop, "checar_cobertura_palavra_a_palavra", lambda *_a, **_k: [])
    monkeypatch.setattr(loop, "conferir_celebrante", lambda *_a, **_k: [])
    monkeypatch.setattr(loop, "_corrigir", lambda *_a, **_k: missa)


def test_ultima_correcao_eh_revalidada_antes_do_veredito(monkeypatch):
    """Montagem corrigida com sucesso NÃO pode sair como pendente.

    Antes da correção, o laço esgotava as iterações e retornava com a lista do
    check ANTERIOR à última correção: a correção era aplicada, nunca verificada,
    e um estado final limpo era reportado como divergente.
    """
    missa = _MissaMinima()
    chamadas = {"conferir": 0}
    _fakes_de_loop(monkeypatch, missa)
    monkeypatch.setattr(loop, "MAX_ITER_CONFERENCIA", 1)

    def conferir_diverge_depois_limpa(*_a, **_k):
        chamadas["conferir"] += 1
        if chamadas["conferir"] == 1:
            return [{"severidade": "baixa", "escopo": "conteudo_liturgico",
                     "detalhe": "divergência que a correção resolve"}]
        return []

    monkeypatch.setattr(loop, "conferir", conferir_diverge_depois_limpa)

    _resultado, meta = loop.montar_com_conferencia(
        b"%PDF-teste", "texto", pdf_celebrante=b"%PDF-celebrante"
    )

    assert chamadas["conferir"] == 2  # revalidou o estado pós-correção
    assert meta["conferida"] is True
    assert meta["iteracoes"] == 1
    assert meta["divergencias_restantes"] == []


def test_veredito_nao_convergido_reflete_o_check_final(monkeypatch):
    """No limite de correções, divergencias_restantes é o estado FINAL, fresco."""
    missa = _MissaMinima()
    chamadas = {"conferir": 0}
    _fakes_de_loop(monkeypatch, missa)
    monkeypatch.setattr(loop, "MAX_ITER_CONFERENCIA", 1)

    def conferir_mudando(*_a, **_k):
        chamadas["conferir"] += 1
        if chamadas["conferir"] == 1:
            return [{"severidade": "baixa", "escopo": "conteudo_liturgico",
                     "detalhe": "divergência antiga (check anterior)"}]
        return [{"severidade": "critica", "escopo": "conteudo_liturgico",
                 "detalhe": "divergência do estado final"}]

    monkeypatch.setattr(loop, "conferir", conferir_mudando)

    _resultado, meta = loop.montar_com_conferencia(
        b"%PDF-teste", "texto", pdf_celebrante=b"%PDF-celebrante"
    )

    assert meta["conferida"] is False
    assert chamadas["conferir"] == 2
    assert meta["iteracoes"] == 1
    assert meta["divergencias_restantes"][0]["detalhe"] == "divergência do estado final"


def test_falha_na_correcao_encerra_com_veredito_fresco(monkeypatch):
    """Se `_corrigir` lança exceção, o veredito é a lista do check que motivou
    a correção (estado não mutado), nunca uma lista vazia ou defasada."""
    missa = _MissaMinima()
    _fakes_de_loop(monkeypatch, missa)
    monkeypatch.setattr(loop, "MAX_ITER_CONFERENCIA", 1)
    monkeypatch.setattr(
        loop, "conferir",
        lambda *_a, **_k: [{"severidade": "baixa", "escopo": "conteudo_liturgico",
                            "detalhe": "divergência que motivou a correção"}],
    )

    def corrigir_falhando(*_a, **_k):
        raise RuntimeError("correção falhou")

    monkeypatch.setattr(loop, "_corrigir", corrigir_falhando)

    _resultado, meta = loop.montar_com_conferencia(
        b"%PDF-teste", "texto", pdf_celebrante=b"%PDF-celebrante"
    )

    assert meta["conferida"] is False
    assert meta["iteracoes"] == 1
    assert meta["divergencias_restantes"][0]["detalhe"] == "divergência que motivou a correção"


# ---------------------------------------------------------------------------
# Contratos de prompt: regra X (silêncio como bloco próprio) e escopo do
# conferente (posição do refrão é derivada por código, não divergência LLM).
# ---------------------------------------------------------------------------

def test_regra_x_manda_silencio_oracao_como_bloco_proprio():
    import re

    from app.llm.prompts import REGRAS_FOLHETO

    m = re.search(
        r'^X\. "MOMENTO DE SILÊNCIO PARA ORAÇÃO PESSOAL".*?(?=^Y\.)',
        REGRAS_FOLHETO, re.S | re.M,
    )
    assert m, "regra X (Momento de silêncio) não encontrada em REGRAS_FOLHETO"
    regra_x = m.group(0)
    assert "BLOCO PRÓPRIO" in regra_x
    assert "numero_folheto null" in regra_x
    # Alinhamento com o gate _tem_silencio e com a convenção das publicadas:
    # título deve conter "silêncio" para o gate achá-lo como bloco.
    assert 'titulo "Momento de silêncio para oração pessoal"' in regra_x


def test_regra_l_nao_contradiz_mais_a_regra_x():
    from app.llm.prompts import REGRAS_FOLHETO

    assert 'Rubricas curtas no fim de um canto ("Momento de silêncio para oração pessoal")' not in REGRAS_FOLHETO
    assert "Única exceção: o \"Momento de silêncio para oração pessoal\" vira" in REGRAS_FOLHETO


def test_conferente_ignora_posicao_do_refrao():
    """posicao_refrao_apos=0 significa refrão ANTES (regra K) — o conferente
    não pode acusar essa posição como divergência litúrgica."""
    assert "posicao_refrao_apos" in loop.INSTR_CONF
    assert "refrão antes das estrofes" in loop.INSTR_CONF
    assert "nunca é divergência por si só" in loop.INSTR_CONF


def test_cobertura_enxerga_celebracao_e_creditos_pydantic():
    """Regressão 07/10: a cobertura nunca pode acusar 'faltando' os créditos e
    a celebração quando eles ESTÃO na montagem.

    A montagem em memória é Pydantic (``titulo_celebracao`` + ``Creditos``);
    antes, ``_texto_montagem`` só lia campos ORM (``celebracao`` + dict) — e a
    cobertura marcava cardeal/kolling/tempesta/comum como omissos em TODA
    montagem nova (falso-positivo MÉDIA que bloqueava a publicação).
    """
    from app.schema.missa import Creditos, Missa, Oracao
    from app.services.auditor_missa import conferir_cobertura_liturgica

    historia = (
        "Hoje celebramos o vigésimo oitavo domingo do tempo comum "
        "e ouvimos a parábola das bodas do filho do rei quando Jesus "
        "voltou a falar em parábolas aos sumos sacerdotes e aos anciãos "
        "do povo dizendo que o reino dos céus é semelhante a um rei que "
        "preparou a festa de casamento do seu filho e enviou os seus servos "
        "para chamar os convidados mas eles não quiseram vir então mandou "
        "outros servos dizendo que o banquete estava pronto com bois e "
        "animais cevados e os convidados porém não deram atenção e foram "
        "um para o seu campo outro para o seu negócio e os demais agarraram "
        "os servos e os maltrataram e os mataram o rei então indignado "
        "enviou as suas tropas e depois disse aos servos que a festa estava "
        "pronta mas os convidados não eram dignos ide pois às encruzilhadas "
        "dos caminhos e convidai todos os que encontrardes tanto maus como "
        "bons e a sala encheu-se de convidados quando o rei entrou viu um "
        "homem sem o traje de festa e mandou amarrá-lo lá fora ali haverá "
        "choro e ranger de dentes "
    )
    montagem = Missa(
        data="2026-10-11",
        ano_liturgico="C",
        titulo_celebracao="28º Domingo do Tempo Comum",
        categoria="Domingo",
        creditos_cantos=Creditos(
            entrada="Ir. Míria T. Kolling",
            ofertas="Fr. Luiz Turra",
            comunhao="Ir. Míria T. Kolling",
            final="Orani João Cardeal Tempesta, O. Cist. e Maestro Marcos Paulo Mendes",
        ),
        blocos=[
            Oracao(
                tipo="oracao", ordem=1,
                titulo="Canto de Entrada",
                texto=historia,
            )
        ],
    )
    fonte = (
        historia
        + "Míria Kolling Turra Orani Cardeal Tempesta Marcos Paulo Mendes "
        + "comum celebrante religiosamente arquidiocesano este convite é para todos"
    )
    achados = conferir_cobertura_liturgica(fonte, montagem)
    detalhes = " ".join(a.detalhe for a in achados).lower()

    # Créditos e celebração estão na montagem → não podem constar como omissos.
    for palavra in ("kolling", "tempesta", "cardeal", "orani", "comum", "mendes"):
        assert palavra not in detalhes, f"falso positivo de cobertura para {palavra!r}: {detalhes}"

    # Controle positivo: palavra verdadeiramente ausente continua sendo acusada.
    assert "religiosamente" in detalhes


# ---------------------------------------------------------------------------
# Numeração do folheto: o montador nunca inventa e o revisor nunca deixa passar.
# ---------------------------------------------------------------------------

def _missa_com_titulos(*titulos):
    blocos = []
    ordem = 0
    for t in titulos:
        ordem += 1
        if "secao" in t or t.startswith("Ritos") or t.startswith("Liturgia") or t.startswith("Eucarística"):
            blocos.append(Secao(ordem=ordem, titulo=t))
        elif "Canto" in t:
            blocos.append(Canto(ordem=ordem, titulo=t, refrao=["refrão"], estrofes=[["estrofe 1"]]))
        elif "Antífona" in t:
            blocos.append(Antifona(ordem=ordem, titulo=t, texto="texto da antífona"))
        else:
            blocos.append(Oracao(ordem=ordem, titulo=t, texto="texto da oração"))
    return Missa(
        data="2026-09-20", ano_liturgico="A", titulo_celebracao="25º Domingo", categoria="domingo",
        creditos_cantos={}, blocos=blocos,
    )


def test_numeracao_limpa_quando_fiel_ao_mapa():
    """Regressão da missa 20/09: números 1..23 com null nas rubricas/apêndice."""
    missa = _missa_com_titulos(
        "Canto de Entrada", "Antífona da Entrada", "Depois da Comunhão", "Leituras da Semana",
    )
    for b, n in zip(missa.blocos, (1, None, 20, None)):
        if hasattr(b, "numero_folheto"):
            b.numero_folheto = n
    mapa = {"blocos": [
        {"titulo": "Canto de Entrada", "numero_impresso": 1},
        {"titulo": "Antífona da Entrada", "numero_impresso": None},
        {"titulo": "Depois da Comunhão", "numero_impresso": 20},
        {"titulo": "Leituras da Semana", "numero_impresso": None},
    ]}

    divs = loop.checar_numeracao_vs_mapa(missa, mapa)

    assert divs == []


def test_numeracao_inventada_para_apendice_e_duplicada_e_regressiva():
    """O 'nunca mais': leituras da semana 27, repetida e fora de ordem é crítico."""
    missa = _missa_com_titulos(
        "Canto de Entrada", "Depois da Comunhão", "Leituras da Semana",
    )
    for b, n in zip(missa.blocos, (20, 27, 27)):
        if hasattr(b, "numero_folheto"):
            b.numero_folheto = n
    mapa = {"blocos": [
        {"titulo": "Canto de Entrada", "numero_impresso": 1},
        {"titulo": "Depois da Comunhão", "numero_impresso": 20},
        {"titulo": "Leituras da Semana", "numero_impresso": None},
    ]}

    divs = loop.checar_numeracao_vs_mapa(missa, mapa)

    detalhes = " ".join(d["detalhe"] for d in divs)
    assert len(divs) >= 3
    assert "27 inventado" in detalhes
    assert "27 repetido" in detalhes
    assert "regride" in detalhes
    assert all(d["severidade"] == "critica" for d in divs)


def test_numeracao_inventada_sem_bloco_no_mapa():
    missa = _missa_com_titulos("Canto de Entrada")
    missa.blocos[0].numero_folheto = 3
    mapa = {"blocos": [{"titulo": "Canto de Entrada", "numero_impresso": 1}]}

    divs = loop.checar_numeracao_vs_mapa(missa, mapa)

    assert [d["detalhe"] for d in divs] == [
        "número 3 inventado: o mapa não numera este bloco"
    ]


def test_numeracao_apendice_sem_bloco_equivalente_no_mapa():
    """Apêndice numerado sem entrada no mapa também é crítico (não vaza na omissão)."""
    missa = _missa_com_titulos("Leituras da Semana")
    missa.blocos[0].numero_folheto = 27
    mapa = {"blocos": [{"titulo": "Leituras da Semana", "numero_impresso": None}]}

    divs = loop.checar_numeracao_vs_mapa(missa, mapa)

    assert any("27 inventado" in d["detalhe"] for d in divs)


def test_bloco_numerado_no_mapa_ausente_na_montagem():
    missa = _missa_com_titulos("Canto de Entrada")
    mapa = {"blocos": [
        {"titulo": "Canto de Entrada", "numero_impresso": 1},
        {"titulo": "Depois da Comunhão", "numero_impresso": 20},
    ]}

    divs = loop.checar_numeracao_vs_mapa(missa, mapa)

    assert any("20 no mapa, ausente na montagem" in d["detalhe"] for d in divs)


def test_sincronizar_numero_folheto_realinha_com_o_mapa():
    """O montador corrige a numeração pela fonte da verdade, sem esperar o laço."""
    missa = _missa_com_titulos(
        "Canto de Entrada", "Antífona da Entrada", "Depois da Comunhão", "Leituras da Semana",
    )
    for b in missa.blocos:
        if hasattr(b, "numero_folheto"):
            b.numero_folheto = 99  # o LLM inventou tudo como 99
    mapa = {"blocos": [
        {"titulo": "Canto de Entrada", "numero_impresso": 1},
        {"titulo": "Antífona da Entrada", "numero_impresso": None},
        {"titulo": "Depois da Comunhão", "numero_impresso": 20},
        {"titulo": "Leituras da Semana", "numero_impresso": None},
    ]}

    loop._sincronizar_numero_folheto(missa, mapa)

    numeros = [getattr(b, "numero_folheto", None) for b in missa.blocos]
    assert numeros == [1, None, 20, None]
    assert loop.checar_numeracao_vs_mapa(missa, mapa) == []


def test_sincronizar_preserva_bloco_sem_correspondencia_no_mapa():
    """Bloco legítimo que o mapa omitiu não é zerado; o revisor decide por ele."""
    missa = _missa_com_titulos("Canto de Entrada", "Rito da Bênção Final")
    missa.blocos[0].numero_folheto = 23
    missa.blocos[1].numero_folheto = 24
    mapa = {"blocos": [{"titulo": "Canto de Entrada", "numero_impresso": 23}]}

    loop._sincronizar_numero_folheto(missa, mapa)

    assert missa.blocos[0].numero_folheto == 23
    assert missa.blocos[1].numero_folheto == 24
    assert any("24 sem bloco correspondente no mapa" in d["detalhe"]
               for d in loop.checar_numeracao_vs_mapa(missa, mapa))


def test_checar_estrutural_inclui_numeracao():
    """A checagem estrutural chamada no laço também valida numeração."""
    missa = _missa_com_titulos("Canto de Entrada", "Leituras da Semana")
    missa.blocos[0].numero_folheto = 1
    missa.blocos[1].numero_folheto = 27
    mapa = {"blocos": [
        {"titulo": "Canto de Entrada", "numero_impresso": 1},
        {"titulo": "Leituras da Semana", "numero_impresso": None},
    ]}

    divs = loop.checar_estrutural_vs_mapa(missa, mapa)

    assert any("27 inventado" in d["detalhe"] for d in divs)


def test_refrao_estrutural_no_mapa_nao_e_divergencia():
    """Regressão da missa 27/09: mapa com repeticoes "Refrão + N estrofes"
    indica a ESTRUTURA normal do canto (refrão intercalado), que a montagem
    representa guardando o refrão UMA única vez no campo `refrao`. O
    INSTR_CONF manda ignorar essa repetição visual — a checagem determinística
    não pode acusá-la como divergência (senão toda missa com cantos de refrão
    fica retida em pendente_revisao)."""
    missa = Missa(
        data="2026-09-27", ano_liturgico="A", titulo_celebracao="26º Domingo do Tempo Comum",
        categoria="domingo", creditos_cantos={},
        blocos=[
            Canto(ordem=2, titulo="Canto de Entrada",
                  refrao=["A Bíblia é a palavra de Deus semeada no meio do povo,"],
                  estrofes=[["Deus é bom, nos ensina a viver.", "Nos revela o caminho a seguir:"],
                            ["Somos povo, o povo de Deus,", "e formamos o Reino de irmãos."]]),
        ],
    )
    mapa = {"blocos": [{"titulo": "Canto de Entrada", "numero_impresso": 1}],
            "repeticoes": [{"onde": "Canto de Entrada", "marca": "Refrão + 2 estrofes"}]}

    divs = loop.checar_estrutural_vs_mapa(missa, mapa)

    assert not any("repetição" in d["detalhe"] or "repeticao" in d["detalhe"] for d in divs)


def test_repeticao_inline_ainda_e_divergencia():
    """Regressão 19/07: repetição "//:" impressa DENTRO das estrofes continua
    sendo divergência quando as estrofes não a repetem (ex.: Canto Final)."""
    missa = Missa(
        data="2026-09-27", ano_liturgico="A", titulo_celebracao="26º Domingo do Tempo Comum",
        categoria="domingo", creditos_cantos={},
        blocos=[
            Canto(ordem=2, titulo="Canto Final",
                  refrao=["Tantas graças temos recebido"],
                  estrofes=[["Do Pai todo amor e todo dom,", "tudo enfim para nós é presente:"]]),
        ],
    )
    mapa = {"blocos": [{"titulo": "Canto Final", "numero_impresso": 1}],
            "repeticoes": [{"onde": "Canto Final", "marca": "//: ://"}]}

    divs = loop.checar_estrutural_vs_mapa(missa, mapa)

    assert any("repetição" in d["detalhe"] for d in divs)


# ------------------------------------------------------- _extrair_json (regressão 11/10)
#
# Em produção (2026-10-11), o conferente Celebrante devolveu o objeto JSON
# completo e TEXTO DEPOIS: json.loads estrito levantou "Extra data: line 4
# column 1 (char 25)" e derrubou uma montagem já paga (US$1,67 por tentativa).

def test_extrair_json_tolerante_a_texto_depois_do_objeto():
    txt = '{\n  "divergencias": []\n}\nConferência concluída sem divergências.'
    assert loop._extrair_json(txt) == {"divergencias": []}


def test_extrair_json_tolerante_a_texto_antes_do_objeto():
    txt = 'Segue o resultado em JSON:\n{"divergencias": [{"campo": "x"}]}'
    assert loop._extrair_json(txt) == {"divergencias": [{"campo": "x"}]}


def test_extrair_json_cerca_markdown_com_texto_extra():
    # _limpar_cercas só remove a cerca quando o texto TERMINA com ``` — aqui
    # há texto depois, então o fallback de raw_decode precisa resolver.
    txt = '```json\n{"divergencias": []}\n```\nObrigado!'
    assert loop._extrair_json(txt) == {"divergencias": []}


def test_extrair_json_sem_json_propaga_erro():
    with pytest.raises(json.JSONDecodeError):
        loop._extrair_json("nada de json neste texto")


def test_extrair_json_lista_nao_passa_como_objeto():
    with pytest.raises(ValueError, match="objeto"):
        loop._extrair_json('[{"divergencias": []}]')


def test_extrair_json_ignora_chave_invalida_antes_do_json_real():
    """Crítico 11/10: `{` inválido em texto explicativo antes do JSON real
    não pode derrubar a extração (raw_decode precisa varrer candidatos)."""
    txt = 'Exemplo de saída: { ... } e o JSON: {"divergencias": []}'
    assert loop._extrair_json(txt) == {"divergencias": []}


def test_extrair_json_lista_com_texto_extra_nao_vira_objeto():
    """Crítico 11/10: `[{...}] + texto` não pode decodificar o elemento INTERNO
    da lista como se fosse o objeto raiz (contrato: lista → erro claro)."""
    with pytest.raises(ValueError, match="objeto"):
        loop._extrair_json('[{"divergencias": []}] fim de texto')


def test_extrair_json_exemplo_no_texto_perde_para_o_payload_real():
    """Crítico 11/10 (mascaramento): um EXEMPLO de JSON completo no texto
    antes da resposta real não pode vencer — aceitaria divergências vazias e
    publicaria sem conferir. O payload maior (a resposta real) deve vencer."""
    txt = ('Formato esperado: {"divergencias": []} (exemplo). Resposta real: '
           '{"divergencias": [{"campo": "x", "detalhe": "divergência real"}]}')
    assert loop._extrair_json(txt) == {
        "divergencias": [{"campo": "x", "detalhe": "divergência real"}]}
