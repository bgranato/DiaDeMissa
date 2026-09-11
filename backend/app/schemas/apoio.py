from typing import Literal

from pydantic import BaseModel


class ApoiosConfiguracaoResponse(BaseModel):
    ativo: bool
    valores_centavos: list[Literal[500, 1000, 1500]]
    reexibir_em_dias: int


class ApoioCheckoutRequest(BaseModel):
    # A lista fechada impede que o cliente imponha preço, moeda ou recorrência.
    valor_centavos: Literal[500, 1000, 1500]
    missa_id: int | None = None


class ApoioCheckoutResponse(BaseModel):
    apoio_id: str
    checkout_url: str


class ApoioStatusResponse(BaseModel):
    status: str
