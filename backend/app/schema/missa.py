from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional, Union

from app.schema.validators import validar_texto_limpo

Postura = Optional[Literal["de_pe", "sentado", "ajoelhado"]]
Falante = Literal["P", "T", "L", "V", "R", "rubrica"]


class Creditos(BaseModel):
    entrada: Optional[str] = None
    ofertas: Optional[str] = None
    comunhao: Optional[str] = None
    final: Optional[str] = None


class PalavraDoDia(BaseModel):
    texto: str
    referencia: str


class BlocoBase(BaseModel):
    ordem: int
    titulo: str
    postura: Postura = None
    subtitulo: Optional[str] = None

    @field_validator("titulo", mode="after")
    @classmethod
    def titulo_limpo(cls, v: str) -> str:
        return validar_texto_limpo(v)


class Secao(BaseModel):
    """Divisor litúrgico (Ritos Iniciais, Liturgia da Palavra etc.)."""
    tipo: Literal["secao"] = "secao"
    ordem: int
    titulo: str
    descricao: Optional[str] = None
    postura: Postura = None


class Canto(BlocoBase):
    tipo: Literal["canto"] = "canto"
    refrao: list[str] = Field(default_factory=list)
    estrofes: list[list[str]] = Field(default_factory=list)
    referencia: Optional[str] = None

    @field_validator("refrao", "estrofes", mode="after")
    @classmethod
    def sem_artefatos(cls, v):
        if isinstance(v, list):
            for item in v:
                if isinstance(item, str):
                    validar_texto_limpo(item)
                elif isinstance(item, list):
                    for s in item:
                        validar_texto_limpo(s)
        return v


class Versiculo(BaseModel):
    numero: int
    texto: str

    @field_validator("texto", mode="after")
    @classmethod
    def texto_limpo(cls, v):
        return validar_texto_limpo(v)


class Leitura(BlocoBase):
    tipo: Literal["leitura"] = "leitura"
    categoria: Literal["primeira_leitura", "segunda_leitura", "evangelho"]
    referencia: str
    introducao: str
    versiculos: list[Versiculo] = Field(default_factory=list)
    conclusao: Optional[str] = None
    resposta: Optional[str] = None


class Salmo(BlocoBase):
    tipo: Literal["salmo"] = "salmo"
    referencia: str
    refrao: list[str]
    estrofes: list[list[str]]


class Aclamacao(BlocoBase):
    tipo: Literal["aclamacao"] = "aclamacao"
    referencia: str
    refrao: list[str]
    versiculo: str


class Antifona(BlocoBase):
    tipo: Literal["antifona"] = "antifona"
    referencia: Optional[str] = None
    texto: str


class Oracao(BlocoBase):
    tipo: Literal["oracao"] = "oracao"
    texto: str
    resposta: Optional[str] = None
    referencia: Optional[str] = None


class Turno(BaseModel):
    falante: Falante
    texto: str

    @field_validator("texto", mode="after")
    @classmethod
    def texto_limpo(cls, v):
        return validar_texto_limpo(v)


class Dialogo(BlocoBase):
    tipo: Literal["dialogo"] = "dialogo"
    turnos: list[Turno]
    referencia: Optional[str] = None


Bloco = Union[Canto, Leitura, Salmo, Aclamacao, Antifona, Oracao, Dialogo, Secao]


class Missa(BaseModel):
    data: str
    ano_liturgico: Literal["A", "B", "C"]
    titulo_celebracao: str
    categoria: str
    descricao: Optional[str] = None
    observacoes: Optional[str] = None
    creditos_cantos: Creditos
    palavra_do_dia: Optional[PalavraDoDia] = None
    blocos: list[Bloco]
