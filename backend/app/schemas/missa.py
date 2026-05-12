from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class BlocoResponse(BaseModel):
    id: int
    ordem: int
    tipo: str
    titulo: Optional[str]
    referencia: Optional[str]
    conteudo: Optional[str]
    conteudo_formatado: Optional[str] = None
    visivel: bool

    class Config:
        from_attributes = True


class MissaResponse(BaseModel):
    id: int
    data: date
    celebracao: Optional[str]
    subtitulo: Optional[str] = None
    descricao: Optional[str] = None
    tempo_liturgico: Optional[str]
    status_processamento: str
    total_blocos: int = 0

    class Config:
        from_attributes = True


class MissaListResponse(BaseModel):
    id: int
    data: date
    celebracao: Optional[str]
    status_processamento: str


class MissaCompletaResponse(BaseModel):
    id: int
    data: date
    celebracao: Optional[str]
    subtitulo: Optional[str] = None
    descricao: Optional[str] = None
    tempo_liturgico: Optional[str]
    fonte_pdf_url: str
    pdf_hash: Optional[str]
    status_processamento: str
    data_criacao: datetime
    blocos: list[BlocoResponse]

    class Config:
        from_attributes = True
