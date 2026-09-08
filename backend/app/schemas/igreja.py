from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class IgrejaBase(BaseModel):
    nome: str
    endereco: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None
    telefone: Optional[str] = None
    site: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    observacoes: Optional[str] = None


class IgrejaCreate(IgrejaBase):
    pass


class IgrejaUpdate(BaseModel):
    nome: Optional[str] = None
    endereco: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None
    telefone: Optional[str] = None
    site: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    observacoes: Optional[str] = None


class LocalizacaoEnderecoRequest(BaseModel):
    """Endereço informado apenas para resolver um ponto de busca; não é persistido."""

    endereco: str = Field(min_length=5, max_length=300)


class IgrejaResponse(IgrejaBase):
    id: int
    data_criacao: datetime
    favorita: bool = False  # populado dinamicamente para o usuário autenticado
    distancia_km: Optional[float] = None  # populado quando há filtro de proximidade

    class Config:
        from_attributes = True
