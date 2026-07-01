"""Persistência best-effort do custo de chamadas de LLM (para o painel admin).

Chamado pelo cliente Anthropic após cada resposta. NUNCA propaga erro — se o
banco estiver indisponível, apenas loga; a montagem do folheto não pode quebrar
por causa da métrica.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def registrar_custo_llm(
    modelo: str,
    tokens_entrada: int,
    tokens_saida: int,
    custo_usd: float,
    contexto: str = "montagem_folheto",
    referencia: Optional[str] = None,
) -> None:
    try:
        from app.core.database import SessionLocal
        from app.models.custo_llm import CustoLLM

        db = SessionLocal()
        try:
            db.add(CustoLLM(
                contexto=contexto,
                referencia=referencia,
                modelo=modelo,
                tokens_entrada=int(tokens_entrada or 0),
                tokens_saida=int(tokens_saida or 0),
                custo_usd=float(custo_usd or 0.0),
            ))
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.exception("Falha ao registrar custo LLM (não bloqueante)")
