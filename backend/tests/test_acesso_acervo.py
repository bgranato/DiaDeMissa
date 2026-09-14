"""Contrato de acesso: o acervo é exclusivo de usuários cadastrados."""
from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api import routes
from app.core.database import get_db
from app.schemas.usuario import HistoricoCreate


def _assert_restrito(chamada) -> None:
    with pytest.raises(HTTPException) as erro:
        chamada()
    assert erro.value.status_code == 403
    assert erro.value.detail == routes.MENSAGEM_CONTEUDO_RESTRITO


def test_busca_agenda_e_pdf_exigem_conta_antes_de_ler_o_acervo():
    _assert_restrito(lambda: routes.buscar_missas(db=None, usuario=None))
    _assert_restrito(lambda: routes.missa_agenda(db=None, usuario=None))
    _assert_restrito(lambda: routes.baixar_pdf_arqrio('2026-09-06', usuario=None))


def test_missa_que_nao_e_publica_exige_conta():
    _assert_restrito(lambda: routes._exigir_missa_publica_ou_conta(None, None, None))


def test_rotas_do_acervo_devolvem_o_aviso_ao_visitante():
    app = FastAPI()
    app.include_router(routes.router)

    def _db_teste():
        yield None

    app.dependency_overrides[get_db] = _db_teste
    app.dependency_overrides[routes.obter_usuario_opcional] = lambda: None
    with TestClient(app) as cliente:
        for url in ('/missas/buscar', '/missa/agenda', '/missas/2026-09-06/pdf-arqrio'):
            resposta = cliente.get(url)
            assert resposta.status_code == 403
            assert resposta.json()['detail'] == routes.MENSAGEM_CONTEUDO_RESTRITO


def test_salvar_progresso_nao_rebaixa_missa_ja_concluida():
    """Reabrir uma missa não pode trocar a conclusão por progresso parcial."""
    registro = type('Registro', (), {
        'percentual_lido': 100.0,
        'ultimo_bloco_id': 23,
        'igreja_id': None,
        'data_ultimo_acesso': None,
    })()

    class Query:
        def __init__(self, resultado):
            self.resultado = resultado

        def filter(self, *_args):
            return self

        def first(self):
            return self.resultado

    class Db:
        def query(self, modelo):
            return Query(object() if modelo is routes.Missa else registro)

        def commit(self):
            pass

    resposta = routes.salvar_progresso(
        HistoricoCreate(missa_id=72, ultimo_bloco_id=1, percentual_lido=7),
        usuario=type('Usuario', (), {'id': 1})(),
        db=Db(),
    )

    assert resposta == {'message': 'Progresso salvo'}
    assert registro.percentual_lido == 100.0
    assert registro.ultimo_bloco_id == 23
