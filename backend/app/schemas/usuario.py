from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr
    celular: Optional[str] = None
    igreja: Optional[str] = None
    senha: str


class UsuarioResponse(BaseModel):
    id: int
    nome: str
    email: str
    celular: Optional[str] = None
    igreja: Optional[str] = None
    is_admin: bool = False
    provider: str
    data_criacao: datetime
    meta_missas_mensal: Optional[int] = None

    class Config:
        from_attributes = True


class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    celular: Optional[str] = None
    igreja: Optional[str] = None


class AdminUsuarioUpdate(BaseModel):
    """Alterações que um admin pode fazer num usuário pelo painel master."""
    is_admin: Optional[bool] = None
    status: Optional[str] = None  # "ativo" | "bloqueado" | "cancelado"


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class LoginGoogleRequest(BaseModel):
    token: str


class LoginGoogleTokenRequest(BaseModel):
    access_token: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str
    nova_senha: str


class AlterarSenhaRequest(BaseModel):
    senha_atual: str
    nova_senha: str


class PreferenciasResponse(BaseModel):
    tamanho_fonte: int = 20
    modo_escuro: bool = False
    alto_contraste: bool = False
    leitura_simplificada: bool = False
    notificacoes_ativas: bool = True
    alerta_missa_email: bool = True

    class Config:
        from_attributes = True


class PreferenciasUpdate(BaseModel):
    tamanho_fonte: Optional[int] = None
    modo_escuro: Optional[bool] = None
    alto_contraste: Optional[bool] = None
    leitura_simplificada: Optional[bool] = None
    notificacoes_ativas: Optional[bool] = None
    alerta_missa_email: Optional[bool] = None


class HistoricoResponse(BaseModel):
    missa_id: int
    data: str
    celebracao: Optional[str]
    ultimo_bloco_id: Optional[int] = None
    percentual_lido: float = 0.0
    data_ultimo_acesso: Optional[datetime] = None
    status: str  # "concluida" | "em_progresso" | "nao_acompanhada"
    igreja_id: Optional[int] = None
    igreja_nome: Optional[str] = None

    class Config:
        from_attributes = True


class HistoricoCreate(BaseModel):
    missa_id: int
    ultimo_bloco_id: int
    percentual_lido: float
    igreja_id: Optional[int] = None


class LembreteCreate(BaseModel):
    missa_id: Optional[int] = None
    titulo: str
    nota: Optional[str] = None
    data_hora_alerta: datetime
    minutos_antecedencia: int = 30
    tipo: str = "usuario"


class LembreteResponse(BaseModel):
    id: int
    missa_id: Optional[int]
    titulo: str
    nota: Optional[str]
    data_hora_alerta: datetime
    minutos_antecedencia: int = 30
    tipo: str = "usuario"
    remetente: str = "Missa do Dia"
    ativo: bool
    lido: bool = False

    class Config:
        from_attributes = True


class LembreteUpdate(BaseModel):
    titulo: Optional[str] = None
    nota: Optional[str] = None
    data_hora_alerta: Optional[datetime] = None
    minutos_antecedencia: Optional[int] = None
    ativo: Optional[bool] = None


class MetaMensalUpdate(BaseModel):
    meta_missas_mensal: Optional[int] = None  # None = remover meta


class LembreteBroadcast(BaseModel):
    titulo: str
    nota: Optional[str] = None
    data_hora_alerta: datetime
    minutos_antecedencia: int = 30
    usuario_id: Optional[int] = None  # None = todos os usuários do segmento
    igreja: Optional[str] = None  # filtra por igreja; None = qualquer
    remetente: Optional[str] = None  # override do remetente exibido (default "Missa do Dia")


class FeedbackCreate(BaseModel):
    tipo: Literal["problema", "sugestao"]
    mensagem: str = Field(min_length=10, max_length=2000)
    email_contato: Optional[EmailStr] = None
    tela: Optional[str] = Field(default=None, max_length=100)


class FeedbackResponse(BaseModel):
    id: int
    tipo: str
    status: str

    class Config:
        from_attributes = True
