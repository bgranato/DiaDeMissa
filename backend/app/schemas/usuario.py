from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


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

    class Config:
        from_attributes = True


class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    celular: Optional[str] = None
    igreja: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class LoginGoogleRequest(BaseModel):
    token: str


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

    class Config:
        from_attributes = True


class PreferenciasUpdate(BaseModel):
    tamanho_fonte: Optional[int] = None
    modo_escuro: Optional[bool] = None
    alto_contraste: Optional[bool] = None
    leitura_simplificada: Optional[bool] = None
    notificacoes_ativas: Optional[bool] = None


class HistoricoResponse(BaseModel):
    missa_id: int
    data: str
    celebracao: Optional[str]
    ultimo_bloco_id: Optional[int] = None
    percentual_lido: float = 0.0
    data_ultimo_acesso: Optional[datetime] = None
    status: str  # "concluida" | "em_progresso" | "nao_acompanhada"

    class Config:
        from_attributes = True


class HistoricoCreate(BaseModel):
    missa_id: int
    ultimo_bloco_id: int
    percentual_lido: float


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

    class Config:
        from_attributes = True


class LembreteUpdate(BaseModel):
    titulo: Optional[str] = None
    nota: Optional[str] = None
    data_hora_alerta: Optional[datetime] = None
    minutos_antecedencia: Optional[int] = None
    ativo: Optional[bool] = None


class LembreteBroadcast(BaseModel):
    titulo: str
    nota: Optional[str] = None
    data_hora_alerta: datetime
    minutos_antecedencia: int = 30
    usuario_id: Optional[int] = None  # None = todos os usuários do segmento
    igreja: Optional[str] = None  # filtra por igreja; None = qualquer
    remetente: Optional[str] = None  # override do remetente exibido (default "Missa do Dia")
