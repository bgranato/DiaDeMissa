"""Contratos de segurança do Gauntlet Loop.

Estes testes cobrem o limite central: falha do crítico ou da referência não
pode ser convertida em aprovação implícita.
"""
from __future__ import annotations

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

    assert len(divergencias) == 1
    assert divergencias[0]["severidade"] == "critica"
    assert divergencias[0]["escopo"] == "conteudo_liturgico"


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
