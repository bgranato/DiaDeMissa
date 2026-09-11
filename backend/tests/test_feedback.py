"""Contrato do canal público de dicas e sugestões."""
from __future__ import annotations

import sys
import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.modules.setdefault("fitz", types.SimpleNamespace())

from app.api import routes
from app.core.database import Base, get_db
from app.models.usuario import FeedbackUsuario


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    app = FastAPI()
    app.include_router(routes.router)

    def _db_teste():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db_teste
    app.dependency_overrides[routes.obter_usuario_opcional] = lambda: None
    app.dependency_overrides[routes.obter_usuario_admin] = lambda: object()
    with TestClient(app) as teste:
        yield teste, Session


def test_visitante_envia_sugestao_e_o_servidor_persiste(client):
    teste, Session = client
    resposta = teste.post("/feedback", json={
        "tipo": "sugestao",
        "mensagem": "Seria ótimo ter uma busca mais visível no início.",
        "email_contato": "fiel@example.com",
        "tela": "home",
    })
    assert resposta.status_code == 201
    assert resposta.json()["tipo"] == "sugestao"
    assert resposta.json()["status"] == "novo"

    db = Session()
    try:
        feedback = db.query(FeedbackUsuario).one()
        assert feedback.usuario_id is None
        assert feedback.email_contato == "fiel@example.com"
        assert feedback.mensagem.startswith("Seria ótimo")
    finally:
        db.close()


def test_feedback_vazio_ou_curto_e_recusado(client):
    teste, _Session = client
    resposta = teste.post("/feedback", json={"tipo": "problema", "mensagem": "curto"})
    assert resposta.status_code == 422


def test_admin_lista_feedback_mais_recente_primeiro(client):
    teste, _Session = client
    teste.post("/feedback", json={"tipo": "problema", "mensagem": "O botão de agenda não abriu para mim."})
    resposta = teste.get("/admin/feedback")
    assert resposta.status_code == 200
    assert resposta.json()["total"] == 1
    assert resposta.json()["feedback"][0]["tipo"] == "problema"
