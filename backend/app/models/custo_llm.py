"""Registro de custo/tokens de cada chamada de LLM — base das métricas de custo
do painel admin. Uma linha por chamada (best-effort; nunca bloqueia a montagem)."""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, DateTime

from app.core.database import Base


class CustoLLM(Base):
    __tablename__ = "custos_llm"

    id = Column(Integer, primary_key=True, index=True)
    data_criacao = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    contexto = Column(String(100), default="montagem_folheto")  # o que gerou o custo
    referencia = Column(String(50), nullable=True)              # ex.: data da missa
    modelo = Column(String(80), nullable=True)
    tokens_entrada = Column(Integer, default=0, nullable=False)
    tokens_saida = Column(Integer, default=0, nullable=False)
    custo_usd = Column(Float, default=0.0, nullable=False)
