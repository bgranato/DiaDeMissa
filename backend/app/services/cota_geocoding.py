"""Freio mensal local para chamadas pagas ao Google Geocoding.

O contador registra somente período e quantidade: endereço, IP e dados da pessoa
não são persistidos. O incremento é um UPSERT atômico para não ultrapassar o teto
em duas requisições simultâneas.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

LIMITE_PADRAO = 10_000
FUSO_FATURAMENTO_GOOGLE = ZoneInfo("America/Los_Angeles")


class ControleGeocodingIndisponivelError(RuntimeError):
    """Falha no freio local; a rota falha fechada para não gerar custo sem controle."""


def limite_mensal() -> int:
    try:
        limite = int(os.getenv("GEOCODING_MENSAL_MAXIMO", str(LIMITE_PADRAO)))
    except (TypeError, ValueError):
        return LIMITE_PADRAO
    return limite if limite > 0 else LIMITE_PADRAO


def periodo_atual() -> str:
    """Período da cota gratuita do Google, que reinicia à meia-noite do Pacífico."""
    return datetime.now(FUSO_FATURAMENTO_GOOGLE).strftime("%Y-%m")


def reservar_consulta(db: Session) -> bool:
    """Reserva uma chamada ao Google e retorna False quando o teto já foi atingido."""
    try:
        resultado = db.execute(
            text(
                """
                INSERT INTO uso_geocoding_mensal (periodo, consultas, atualizado_em)
                VALUES (:periodo, 1, CURRENT_TIMESTAMP)
                ON CONFLICT (periodo) DO UPDATE
                SET consultas = uso_geocoding_mensal.consultas + 1,
                    atualizado_em = CURRENT_TIMESTAMP
                WHERE uso_geocoding_mensal.consultas < :limite
                RETURNING consultas
                """
            ),
            {"periodo": periodo_atual(), "limite": limite_mensal()},
        ).first()
        db.commit()
        return resultado is not None
    except SQLAlchemyError as erro:
        db.rollback()
        logger.exception("Falha ao reservar cota mensal de Geocoding")
        raise ControleGeocodingIndisponivelError("freio mensal indisponível") from erro
