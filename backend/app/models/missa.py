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
    # Versão das regras de montagem que produziram esta missa (<hash8>+<modelo>).
    # null = montada por versão ANTIGA (antes do versionamento) → candidata a
    # reprocesso automático. Ver app/core/pipeline_version.py.
    pipeline_version = Column(String(80), nullable=True)
    status_processamento = Column(String(50), default="pendente")
    # Resultado do gate de fidelidade PDF×montagem (divergências) — para o admin
    # revisar as missas em pendente_revisao. {ok, criticas:[...], todas:[...]}.
    revisao_json = Column(JSON, nullable=True)
    # Controle do alerta por e-mail "missa disponível": garante envio 1x por missa.
    alerta_email_enviado = Column(Boolean, default=False, nullable=False)
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
