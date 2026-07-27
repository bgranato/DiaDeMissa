"""Testes dos freios de gasto (orçamento diário, teto/missa, disjuntor 402)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.custo_llm import CustoLLM
import app.core.database as dbmod
from app.services import freios_gasto as fg


@pytest.fixture()
def env(monkeypatch, tmp_path):
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=eng, tables=[CustoLLM.__table__])
    Session = sessionmaker(bind=eng)
    monkeypatch.setattr(dbmod, "SessionLocal", Session)
    monkeypatch.setenv("FREIOS_STATE_FILE", str(tmp_path / "freios.json"))
    monkeypatch.setenv("MONITOR_TETO_DIARIO", "3")
    monkeypatch.setenv("MONITOR_MAX_TENTATIVAS_MISSA_DIA", "2")
    return Session


def _gasto(Session, usd):
    s = Session()
    s.add(CustoLLM(contexto="conv:montagem", modelo="m", tokens_entrada=1, tokens_saida=1, custo_usd=usd))
    s.commit(); s.close()


# --- 2b: orçamento diário ---
def test_orcamento_diario_bloqueia(env):
    Session = env
    _gasto(Session, 1.5)
    assert fg.gasto_do_dia() == 1.5
    ok, _ = fg.pode_montar("2026-07-27")
    assert ok is True
    _gasto(Session, 2.0)  # total 3.5 >= 3
    ok, motivo = fg.pode_montar("2026-07-27")
    assert ok is False and "orçamento" in motivo


# --- 2a: teto de tentativas/dia por missa ---
def test_teto_tentativas_por_missa(env):
    assert fg.tentativas_hoje("2026-07-27") == 0
    fg.registrar_tentativa("2026-07-27")
    fg.registrar_tentativa("2026-07-27")
    ok, motivo = fg.pode_montar("2026-07-27")
    assert ok is False and "tentativas" in motivo
    # outra missa não é afetada
    ok2, _ = fg.pode_montar("2026-07-28")
    assert ok2 is True


# --- 2a: disjuntor de crédito (402) ---
def test_disjuntor_credito(env):
    ok, _ = fg.pode_montar("2026-07-27")
    assert ok is True
    fg.bloquear_credito("402 anthropic")
    assert fg.credito_bloqueado() is True
    ok, motivo = fg.pode_montar("2026-07-27")
    assert ok is False and "disjuntor" in motivo
    # só libera manualmente / após sucesso pago
    fg.liberar_credito()
    assert fg.credito_bloqueado() is False
    ok, _ = fg.pode_montar("2026-07-27")
    assert ok is True


def test_disjuntor_tem_prioridade_sobre_orcamento(env):
    Session = env
    _gasto(Session, 10.0)  # orçamento estourado
    fg.bloquear_credito("402")
    ok, motivo = fg.pode_montar("2026-07-27")
    assert ok is False and "disjuntor" in motivo  # disjuntor vem primeiro
