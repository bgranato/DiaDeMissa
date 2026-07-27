"""Freios de gasto de LLM — nenhum processo automático pode gastar ilimitado.

Três freios, todos consultados por `pode_montar(data_missa)` antes de qualquer montagem:

  a) DISJUNTOR DE CRÉDITO (402): ao detectar erro de crédito/quota, `bloquear_credito()`
     trava novas montagens até `liberar_credito()` — que só acontece após o SUCESSO de
     uma chamada paga (prova que há saldo) ou flag manual. Enquanto travado, missas ficam
     pendente_revisao (o alerta de emergência já avisou).
  b) TETO DE TENTATIVAS/DIA POR MISSA: no máx. MONITOR_MAX_TENTATIVAS_MISSA_DIA (default 2)
     montagens por (missa, dia). Evita retry em loop da mesma missa.
  c) ORÇAMENTO DIÁRIO: se o gasto do dia em custo_llm passar de MONITOR_TETO_DIARIO
     (default US$ 3), pausa montagens automáticas + e-mail de alerta.

Estado persistido em data/freios_gasto.json (compartilhado pelos workers). Path via
FREIOS_STATE_FILE (usado nos testes).
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _hoje() -> str:
    return _agora().date().isoformat()


# ------------------------------------------------------------------ config
def teto_diario() -> float:
    try:
        return float(os.getenv("MONITOR_TETO_DIARIO", "3"))
    except (TypeError, ValueError):
        return 3.0


def max_tentativas_dia() -> int:
    try:
        return int(os.getenv("MONITOR_MAX_TENTATIVAS_MISSA_DIA", "2"))
    except (TypeError, ValueError):
        return 2


# ------------------------------------------------------------------ estado (json)
def _state_path() -> Path:
    p = os.getenv("FREIOS_STATE_FILE", "").strip()
    if p:
        return Path(p)
    return Path(__file__).resolve().parents[2] / "data" / "freios_gasto.json"


def _load() -> dict:
    try:
        return json.loads(_state_path().read_text("utf-8"))
    except Exception:
        return {}


def _save(d: dict) -> None:
    try:
        fp = _state_path()
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(json.dumps(d), "utf-8")
    except Exception:
        logger.exception("freios: falha ao salvar estado")


# ------------------------------------------------------------------ gasto do dia
def gasto_do_dia() -> float:
    """Soma custo_usd de hoje (UTC), excluindo linhas de erro_credito (custo 0)."""
    from datetime import datetime as _dt
    from app.core.database import SessionLocal
    from app.models.custo_llm import CustoLLM
    inicio = _dt.combine(_agora().date(), _dt.min.time(), tzinfo=timezone.utc)
    db = SessionLocal()
    try:
        rows = db.query(CustoLLM).filter(
            CustoLLM.data_criacao >= inicio,
            CustoLLM.contexto != "erro_credito",
        ).all()
        return round(sum(float(r.custo_usd or 0.0) for r in rows), 4)
    finally:
        db.close()


def orcamento_estourado() -> bool:
    return gasto_do_dia() >= teto_diario()


# ------------------------------------------------------------------ tentativas/dia/missa
def tentativas_hoje(data_missa: str) -> int:
    d = _load()
    return int((d.get("tentativas", {}).get(_hoje(), {})).get(data_missa, 0))


def registrar_tentativa(data_missa: str) -> int:
    d = _load()
    tent = d.setdefault("tentativas", {})
    hoje = tent.setdefault(_hoje(), {})
    hoje[data_missa] = int(hoje.get(data_missa, 0)) + 1
    # limpa dias antigos (mantém só hoje)
    d["tentativas"] = {_hoje(): hoje}
    _save(d)
    return hoje[data_missa]


# ------------------------------------------------------------------ disjuntor de crédito
def credito_bloqueado() -> bool:
    return bool(_load().get("credito_bloqueado"))


def bloquear_credito(motivo: str = "") -> None:
    d = _load()
    d["credito_bloqueado"] = {"desde": _agora().isoformat(), "motivo": motivo[:200]}
    _save(d)
    logger.warning("freios: DISJUNTOR de crédito ATIVADO — %s", motivo[:120])


def liberar_credito() -> None:
    d = _load()
    if d.pop("credito_bloqueado", None) is not None:
        _save(d)
        logger.info("freios: disjuntor de crédito liberado")


# ------------------------------------------------------------------ decisão
def pode_montar(data_missa: str) -> tuple[bool, str]:
    """(pode, motivo). Ordem: disjuntor de crédito → orçamento diário → teto/missa."""
    if credito_bloqueado():
        return False, "disjuntor de crédito ativo (402) — aguardando recarga/sonda ou liberação manual"
    gasto = gasto_do_dia()
    teto = teto_diario()
    if gasto >= teto:
        return False, f"orçamento diário estourado: US$ {gasto:.2f} ≥ teto US$ {teto:.2f}"
    n = tentativas_hoje(data_missa)
    if n >= max_tentativas_dia():
        return False, f"teto de tentativas/dia atingido para {data_missa}: {n}/{max_tentativas_dia()}"
    return True, "ok"
