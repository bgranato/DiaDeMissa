"""Contratos de segurança do Gauntlet Loop.

Estes testes cobrem o limite central: falha do crítico ou da referência não
pode ser convertida em aprovação implícita.
"""
from __future__ import annotations

import pytest

from app.pipeline import montagem_convergente as loop


class _MissaMinima:
    def model_dump(self):
        return {"blocos": []}


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
    monkeypatch.setattr(
        loop,
        "conferir",
        lambda *_args, **_kwargs: [{"severidade": "baixa", "escopo": "conteudo_liturgico"}],
    )
    monkeypatch.setattr(loop, "_corrigir", lambda *_args, **_kwargs: missa)

    _resultado, meta = loop.montar_com_conferencia(b"%PDF-teste", "texto")

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
