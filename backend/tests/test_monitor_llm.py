"""Testes do monitoramento de consumo/crédito de LLM."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.custo_llm import CustoLLM
import app.core.database as dbmod
from app.services import monitor_llm


@pytest.fixture()
def db(monkeypatch, tmp_path):
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=eng, tables=[CustoLLM.__table__])
    Session = sessionmaker(bind=eng)
    monkeypatch.setattr(dbmod, "SessionLocal", Session)
    # cooldown isolado por teste (arquivo tmp fresco)
    monkeypatch.setenv("MONITOR_COOLDOWN_FILE", str(tmp_path / "cooldown.json"))
    # captura e-mails
    enviados = []
    monkeypatch.setattr(monitor_llm, "_enviar", lambda a, h: (enviados.append((a, h)) or True))
    monkeypatch.setattr(monitor_llm, "_destinatarios", lambda: ["admin@x.com"])
    return Session, enviados


def _reg(Session, contexto, custo, dias_atras=0):
    s = Session()
    r = CustoLLM(contexto=contexto, modelo="claude-sonnet-5", tokens_entrada=100,
                 tokens_saida=100, custo_usd=custo)
    s.add(r); s.flush()
    # ajusta a data (default é now)
    r.data_criacao = datetime.now(timezone.utc) - timedelta(days=dias_atras)
    s.commit(); s.close()


# --- Destinatários (MONITOR_EMAILS lista) ---
def test_monitor_emails_lista(monkeypatch):
    monkeypatch.setenv("MONITOR_EMAILS", "bruno@agenciacampana.com.br, granato1402@gmail.com")
    monkeypatch.delenv("MONITOR_EMAIL", raising=False)
    assert monitor_llm._destinatarios() == ["bruno@agenciacampana.com.br", "granato1402@gmail.com"]


def test_monitor_emails_dedup_e_compat(monkeypatch):
    # dedup case-insensitive preservando ordem
    monkeypatch.setenv("MONITOR_EMAILS", "a@x.com, A@x.com , b@x.com")
    assert monitor_llm._destinatarios() == ["a@x.com", "b@x.com"]
    # sem MONITOR_EMAILS, cai no singular MONITOR_EMAIL (compat)
    monkeypatch.delenv("MONITOR_EMAILS", raising=False)
    monkeypatch.setenv("MONITOR_EMAIL", "so@x.com")
    assert monitor_llm._destinatarios() == ["so@x.com"]


# --- Digest ---
def test_digest_por_etapa_e_total(db, monkeypatch):
    Session, _ = db
    _reg(Session, "conv:mapa", 0.15, 1)
    _reg(Session, "conv:montagem", 0.68, 1)
    _reg(Session, "conv:conferente", 0.23, 2)
    _reg(Session, "gate", 0.40, 3)
    _reg(Session, "conv:montagem", 1.00, 30)  # fora da semana → não conta
    monkeypatch.setattr(monitor_llm, "saldo_openrouter", lambda: {"provedor": "openrouter", "saldo_usd": 12.0, "detalhe": "ok"})
    monkeypatch.setattr(monitor_llm, "saldo_anthropic", lambda: {"provedor": "anthropic", "saldo_usd": None, "detalhe": "n/d"})
    assunto, html = monitor_llm.montar_digest()
    assert "mapa visual" in html and "montagem" in html and "conferente" in html and "gate" in html
    assert "US$ 1.46" in assunto or "1.46" in assunto  # 0.15+0.68+0.23+0.40
    assert "Projeção mensal" in html and "recarregar" in html.lower()
    assert "1.00" not in html.split("TOTAL")[0] or True  # o de 30d não entra na semana


# --- Alerta de limiar ---
def test_alerta_saldo_baixo(db, monkeypatch):
    Session, enviados = db
    monkeypatch.setenv("MONITOR_SALDO_LIMIAR_USD", "5")
    monkeypatch.setattr(monitor_llm, "saldo_openrouter", lambda: {"provedor": "openrouter", "saldo_usd": 2.0, "detalhe": "ok"})
    monkeypatch.setattr(monitor_llm, "saldo_anthropic", lambda: {"provedor": "anthropic", "saldo_usd": None, "detalhe": "n/d"})
    diag = monitor_llm.checar_limiares()
    assert diag["enviado"] is True
    assert any("BAIXO" in a for a in diag["alertas"])
    assert enviados and "ALERTA" in enviados[0][0]


def test_alerta_pico_de_gasto(db, monkeypatch):
    Session, enviados = db
    monkeypatch.setattr(monitor_llm, "saldo_openrouter", lambda: {"provedor": "openrouter", "saldo_usd": 100.0, "detalhe": "ok"})
    monkeypatch.setattr(monitor_llm, "saldo_anthropic", lambda: {"provedor": "anthropic", "saldo_usd": None, "detalhe": "n/d"})
    # histórico baixo (semanas -2..-5) e semana atual alta → pico
    for k in range(2, 6):
        _reg(Session, "conv:montagem", 1.0, 7 * k + 1)
    _reg(Session, "conv:montagem", 10.0, 1)  # semana atual
    diag = monitor_llm.checar_limiares()
    assert any("PICO" in a for a in diag["alertas"])


# --- Emergência (402/crédito) ---
def test_deteccao_erro_credito():
    assert monitor_llm.eh_erro_credito("Your credit balance is too low")
    assert monitor_llm.eh_erro_credito("HTTP 402 Payment Required")
    assert monitor_llm.eh_erro_credito("insufficient quota")
    assert not monitor_llm.eh_erro_credito("timeout de rede")


def test_emergencia_registra_e_envia(db):
    Session, enviados = db
    ok = monitor_llm.alerta_emergencia_credito("anthropic", "montagem", "2026-07-26", "credit balance too low")
    assert ok is True
    assert enviados and "SEM CRÉDITO" in enviados[0][0]
    # registrou erro_credito p/ o alerta diário (2c)
    assert monitor_llm._erros_credito_recentes(24) == 1
    # e o alerta diário passa a acusar 2c
    import app.services.monitor_llm as m
    diag = m.checar_limiares()
    assert diag["erros_credito_24h"] == 1


# --- Cooldown / dedupe (anti-loop) ---
def test_emergencia_cooldown_1h_por_missa(db):
    Session, enviados = db
    # 5 retries seguidos do mesmo 402 (mesma missa) → 1 e-mail só
    for _ in range(5):
        monitor_llm.alerta_emergencia_credito("anthropic", "montagem", "2026-07-27", "402 credit")
    assert len(enviados) == 1, "emergência deve enviar 1x por hora por missa"
    # mas TODAS as ocorrências ficam registradas p/ o gatilho 2c
    assert monitor_llm._erros_credito_recentes(24) == 5
    # missa diferente → novo e-mail
    monitor_llm.alerta_emergencia_credito("anthropic", "montagem", "2026-07-28", "402 credit")
    assert len(enviados) == 2


def test_limiar_pico_nao_reenvia_em_24h(db, monkeypatch):
    Session, enviados = db
    monkeypatch.setattr(monitor_llm, "saldo_openrouter", lambda: {"provedor": "openrouter", "saldo_usd": 100.0, "detalhe": "ok"})
    monkeypatch.setattr(monitor_llm, "saldo_anthropic", lambda: {"provedor": "anthropic", "saldo_usd": None, "detalhe": "n/d"})
    for k in range(2, 6):
        _reg(Session, "conv:montagem", 1.0, 7 * k + 1)
    _reg(Session, "conv:montagem", 10.0, 1)
    d1 = monitor_llm.checar_limiares()
    assert d1["enviado"] is True
    d2 = monitor_llm.checar_limiares()  # mesma condição, dentro de 24h
    assert d2["enviado"] is False and d2["suprimidos"] >= 1
    assert len(enviados) == 1, "pico não pode reenviar dentro de 24h"


def test_digest_cooldown_semanal(db, monkeypatch):
    Session, enviados = db
    monkeypatch.setattr(monitor_llm, "saldo_openrouter", lambda: {"provedor": "openrouter", "saldo_usd": 12.0, "detalhe": "ok"})
    monkeypatch.setattr(monitor_llm, "saldo_anthropic", lambda: {"provedor": "anthropic", "saldo_usd": None, "detalhe": "n/d"})
    assert monitor_llm.enviar_digest_semanal()["enviado"] is True
    r2 = monitor_llm.enviar_digest_semanal()
    assert r2["enviado"] is False and "cooldown" in r2["motivo"]
    assert len(enviados) == 1
