"""Contador mensal de chamadas ao Geocoding, sem guardar endereços."""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from app.core.database import Base


class UsoGeocodingMensal(Base):
    """Uma linha por período de faturamento, usada para proteger a cota mensal."""

    __tablename__ = "uso_geocoding_mensal"

    periodo = Column(String(7), primary_key=True)  # YYYY-MM no fuso do faturamento Google
    consultas = Column(Integer, nullable=False, default=0)
    atualizado_em = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
