from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class Missa(Base):
    __tablename__ = "missas"

    id = Column(Integer, primary_key=True, index=True)
    data = Column(Date, unique=True, nullable=False, index=True)
    celebracao = Column(String(255), nullable=True)
    subtitulo = Column(String(500), nullable=True)
    descricao = Column(Text, nullable=True)
    tempo_liturgico = Column(String(100), nullable=True)
    ano_liturgico = Column(String(1), nullable=True)
    categoria = Column(String(100), nullable=True)
    observacoes = Column(Text, nullable=True)
    creditos_cantos = Column(JSON, nullable=True)
    palavra_do_dia = Column(JSON, nullable=True)
    fonte_pdf_url = Column(String(500), nullable=False)
    pdf_hash = Column(String(64), nullable=True)
    status_processamento = Column(String(50), default="pendente")
    data_criacao = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    blocos = relationship("BlocoLiturgico", back_populates="missa", order_by="BlocoLiturgico.ordem")


class BlocoLiturgico(Base):
    __tablename__ = "blocos_liturgicos"

    id = Column(Integer, primary_key=True, index=True)
    missa_id = Column(Integer, ForeignKey("missas.id"), nullable=False)
    ordem = Column(Integer, nullable=False)
    tipo = Column(String(100), nullable=False)
    titulo = Column(String(255), nullable=True)
    referencia = Column(String(255), nullable=True)
    conteudo = Column(Text, nullable=True)
    conteudo_formatado = Column(Text, nullable=True)
    conteudo_estruturado = Column(JSON, nullable=True)
    observacoes = Column(Text, nullable=True)
    visivel = Column(Boolean, default=True)

    missa = relationship("Missa", back_populates="blocos")
