from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Apoio(Base):
    """Registro mínimo de uma contribuição voluntária via provedor externo.

    Não persistimos dados de cartão, Pix, CPF ou payload bruto do provedor.
    O identificador público é opaco e serve de referência entre Checkout Pro e
    o webhook assinado do Mercado Pago.
    """

    __tablename__ = "apoios"
    __table_args__ = (Index("ix_apoios_status_criado", "status", "criado_em"),)

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, index=True)
    missa_id = Column(Integer, ForeignKey("missas.id"), nullable=True, index=True)
    valor_centavos = Column(Integer, nullable=False)
    moeda = Column(String(3), nullable=False, default="BRL")
    status = Column(String(40), nullable=False, default="iniciado")
    provedor = Column(String(40), nullable=False, default="mercado_pago")
    preference_id = Column(String(120), unique=True, nullable=True, index=True)
    payment_id = Column(String(120), unique=True, nullable=True, index=True)
    metodo_pagamento = Column(String(80), nullable=True)
    criado_em = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    atualizado_em = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    confirmado_em = Column(DateTime(timezone=True), nullable=True)

    usuario = relationship("Usuario")
    missa = relationship("Missa")
