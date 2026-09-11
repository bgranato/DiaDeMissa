"""Contrato do apoio voluntário: preço fechado e confirmação só pelo webhook."""
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
from app.models.apoio import Apoio


@pytest.fixture()
def client(monkeypatch):
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
    monkeypatch.setattr(routes, "mercado_pago_configurado", lambda: True)
    with TestClient(app) as teste:
        yield teste, Session


def test_configuracao_nao_expoe_apoio_sem_configuracao(monkeypatch):
    monkeypatch.setattr(routes, "mercado_pago_configurado", lambda: False)
    app = FastAPI()
    app.include_router(routes.router)
    with TestClient(app) as cliente:
        resposta = cliente.get("/apoios/configuracao")
    assert resposta.status_code == 200
    assert resposta.json() == {"ativo": False, "valores_centavos": [500, 1000, 1500], "reexibir_em_dias": 1}


def test_checkout_aceita_somente_valores_fechados(client, monkeypatch):
    teste, Session = client
    chamadas = []
    monkeypatch.setattr(routes, "criar_checkout", lambda **kwargs: chamadas.append(kwargs) or ("https://www.mercadopago.com/checkout", "pref_1"))

    invalido = teste.post("/apoios/checkout", json={"valor_centavos": 501})
    assert invalido.status_code == 422

    resposta = teste.post("/apoios/checkout", json={"valor_centavos": 1000})
    assert resposta.status_code == 201
    assert resposta.json()["checkout_url"].startswith("https://")
    assert chamadas[0]["valor_centavos"] == 1000

    db = Session()
    try:
        apoio = db.query(Apoio).one()
        assert apoio.valor_centavos == 1000
        assert apoio.status == "aguardando_pagamento"
        assert apoio.preference_id == "pref_1"
    finally:
        db.close()


def test_webhook_nao_confirma_sem_assinatura_valida(client, monkeypatch):
    teste, _Session = client
    monkeypatch.setattr(routes, "validar_assinatura_webhook", lambda **_kwargs: False)
    resposta = teste.post("/apoios/mercadopago/webhook?data.id=123", json={"data": {"id": "123"}})
    assert resposta.status_code == 401


def test_webhook_confere_referencia_valor_e_moeda_antes_de_aprovar(client, monkeypatch):
    teste, Session = client
    monkeypatch.setattr(routes, "criar_checkout", lambda **_kwargs: ("https://www.mercadopago.com/checkout", "pref_2"))
    checkout = teste.post("/apoios/checkout", json={"valor_centavos": 500}).json()
    monkeypatch.setattr(routes, "validar_assinatura_webhook", lambda **_kwargs: True)
    monkeypatch.setattr(routes, "consultar_pagamento", lambda _payment_id: {
        "external_reference": checkout["apoio_id"],
        "transaction_amount": 5,
        "currency_id": "BRL",
        "status": "approved",
        "payment_type_id": "pix",
    })

    resposta = teste.post("/apoios/mercadopago/webhook?data.id=pay_1", json={"data": {"id": "pay_1"}})
    assert resposta.status_code == 200

    db = Session()
    try:
        apoio = db.query(Apoio).filter(Apoio.public_id == checkout["apoio_id"]).one()
        assert apoio.status == "approved"
        assert apoio.payment_id == "pay_1"
        assert apoio.metodo_pagamento == "pix"
        assert apoio.confirmado_em is not None
    finally:
        db.close()


def test_webhook_bloqueia_aprovacao_com_valor_divergente(client, monkeypatch):
    teste, Session = client
    monkeypatch.setattr(routes, "criar_checkout", lambda **_kwargs: ("https://www.mercadopago.com/checkout", "pref_3"))
    checkout = teste.post("/apoios/checkout", json={"valor_centavos": 1500}).json()
    monkeypatch.setattr(routes, "validar_assinatura_webhook", lambda **_kwargs: True)
    monkeypatch.setattr(routes, "consultar_pagamento", lambda _payment_id: {
        "external_reference": checkout["apoio_id"],
        "transaction_amount": 5,
        "currency_id": "BRL",
        "status": "approved",
    })

    resposta = teste.post("/apoios/mercadopago/webhook?data.id=pay_2", json={"data": {"id": "pay_2"}})
    assert resposta.status_code == 200
    db = Session()
    try:
        assert db.query(Apoio).filter(Apoio.public_id == checkout["apoio_id"]).one().status == "divergencia_pagamento"
    finally:
        db.close()


def test_webhook_bloqueia_valor_com_fracao_de_centavo(client, monkeypatch):
    teste, Session = client
    monkeypatch.setattr(routes, "criar_checkout", lambda **_kwargs: ("https://www.mercadopago.com/checkout", "pref_4"))
    checkout = teste.post("/apoios/checkout", json={"valor_centavos": 500}).json()
    monkeypatch.setattr(routes, "validar_assinatura_webhook", lambda **_kwargs: True)
    monkeypatch.setattr(routes, "consultar_pagamento", lambda _payment_id: {
        "external_reference": checkout["apoio_id"],
        "transaction_amount": "5.001",
        "currency_id": "BRL",
        "status": "approved",
    })

    assert teste.post("/apoios/mercadopago/webhook?data.id=pay_3", json={"data": {"id": "pay_3"}}).status_code == 200
    db = Session()
    try:
        assert db.query(Apoio).filter(Apoio.public_id == checkout["apoio_id"]).one().status == "divergencia_pagamento"
    finally:
        db.close()
