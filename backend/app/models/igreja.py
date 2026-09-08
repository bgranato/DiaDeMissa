"""Modelos de Igreja e relacionamento Usuario↔Igreja (favoritas).

Fase 1 do feature "Igrejas": catálogo simples + favoritos por usuário.
Geo (lat/lng) já incluídos pra Fase 2 (proximidade no mapa).
"""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class Igreja(Base):
    __tablename__ = "igrejas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False, index=True)
    endereco = Column(String(500), nullable=True)
    cidade = Column(String(120), nullable=True, index=True)
    estado = Column(String(2), nullable=True)
    cep = Column(String(20), nullable=True)
    telefone = Column(String(40), nullable=True)
    site = Column(String(255), nullable=True)
    # Geolocalização (preenchida via Nominatim ou cadastro manual)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    observacoes = Column(Text, nullable=True)
    # Mapeia pro id do local de culto no site da Arquidiocese RJ — usado pra buscar horários
    arqrio_local_id = Column(Integer, nullable=True, index=True)
    # Horários (texto multi-linha: "Missa: Dom 7h, 9h, 11h | Seg 19h | ...")
    horarios_missa = Column(Text, nullable=True)
    data_criacao = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    favoritada_por = relationship("UsuarioIgreja", back_populates="igreja", cascade="all, delete-orphan")


class UsuarioIgreja(Base):
    """Junction: igrejas favoritas de cada usuário."""
    __tablename__ = "usuario_igrejas"
    __table_args__ = (UniqueConstraint("usuario_id", "igreja_id", name="uq_usuario_igreja"),)

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    igreja_id = Column(Integer, ForeignKey("igrejas.id", ondelete="CASCADE"), nullable=False, index=True)
    data_salva = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    igreja = relationship("Igreja", back_populates="favoritada_por")
