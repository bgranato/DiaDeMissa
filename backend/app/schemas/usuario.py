from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str


class UsuarioResponse(BaseModel):
    id: int
    nome: str
    email: str
    provider: str
    data_criacao: datetime

    class Config:
        from_attributes = True


class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class LoginGoogleRequest(BaseModel):
    token: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse


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
    ultimo_bloco_id: Optional[int]
    percentual_lido: float
    data_ultimo_acesso: datetime

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
    usuario_id: Optional[int] = None  # None = todos
