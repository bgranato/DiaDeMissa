from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, Index, text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    celular = Column(String(20), nullable=True)
    senha_hash = Column(String(255), nullable=True)
    provider = Column(String(50), default="email")
    provider_id = Column(String(255), nullable=True)
    igreja = Column(String(200), nullable=True, index=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    # Estado do cadastro para o painel admin: "ativo" | "bloqueado" | "cancelado".
    status = Column(String(20), default="ativo", nullable=False)
    reset_token = Column(String(255), nullable=True, index=True)
    reset_token_expira = Column(DateTime(timezone=True), nullable=True)
    # Meta de missas por mês (Jornada). Null = sem meta — sistema ainda contabiliza
    # frequência contra "dias com missa" e "domingos+solenidades recomendado".
    meta_missas_mensal = Column(Integer, nullable=True)
    data_criacao = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    data_atualizacao = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    preferencias = relationship("PreferenciaUsuario", back_populates="usuario", uselist=False)
    historico = relationship("HistoricoUsuario", back_populates="usuario")
    lembretes = relationship("Lembrete", back_populates="usuario")


class PreferenciaUsuario(Base):
    __tablename__ = "preferencias_usuario"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), unique=True, nullable=False)
    tamanho_fonte = Column(Integer, default=20)
    modo_escuro = Column(Boolean, default=False)
    alto_contraste = Column(Boolean, default=False)
    leitura_simplificada = Column(Boolean, default=False)
    notificacoes_ativas = Column(Boolean, default=True)

    usuario = relationship("Usuario", back_populates="preferencias")


class HistoricoUsuario(Base):
    __tablename__ = "historico_usuario"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    missa_id = Column(Integer, ForeignKey("missas.id"), nullable=False)
    igreja_id = Column(Integer, ForeignKey("igrejas.id"), nullable=True)  # onde a pessoa assistiu
    ultimo_bloco_id = Column(Integer, nullable=True)
    percentual_lido = Column(Float, default=0.0)
    data_ultimo_acesso = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    usuario = relationship("Usuario", back_populates="historico")


class Lembrete(Base):
    __tablename__ = "lembretes"

    # Impede duplicar a notificação automática "não acompanhou" do mesmo usuário
    # para a mesma missa. Índice PARCIAL: só vale para tipo='nao_acompanhada',
    # então lembretes do usuário e broadcasts (master) podem repetir normalmente.
    __table_args__ = (
        Index(
            "uq_lembrete_nao_acompanhada",
            "usuario_id", "missa_id",
            unique=True,
            postgresql_where=text("tipo = 'nao_acompanhada'"),
            sqlite_where=text("tipo = 'nao_acompanhada'"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    missa_id = Column(Integer, ForeignKey("missas.id"), nullable=True)
    titulo = Column(String(255), nullable=False)
    nota = Column(Text, nullable=True)
    data_hora_alerta = Column(DateTime(timezone=True), nullable=False)
    minutos_antecedencia = Column(Integer, default=30)
    tipo = Column(String(50), default="usuario")
    remetente = Column(String(255), default="Missa do Dia")
    ativo = Column(Boolean, default=True)
    lido = Column(Boolean, default=False, nullable=False)

    usuario = relationship("Usuario", back_populates="lembretes")
