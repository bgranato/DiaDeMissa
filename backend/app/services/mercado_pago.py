"""Integração server-to-server com o Checkout Pro do Mercado Pago."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from urllib.parse import urlparse

import httpx
from mercadopago.webhook import InvalidWebhookSignatureError, WebhookSignatureValidator

from app.core.config import settings

CHECKOUT_PREFERENCES_URL = "https://api.mercadopago.com/checkout/preferences"
PAYMENTS_URL = "https://api.mercadopago.com/v1/payments"
VALORES_PERMITIDOS = frozenset({500, 1000, 1500})


class MercadoPagoErro(RuntimeError):
    """Erro seguro para o cliente; detalhes ficam somente nos logs do servidor."""


def configurado() -> bool:
    return bool(settings.APOIOS_ATIVOS and settings.MERCADOPAGO_ACCESS_TOKEN and settings.MERCADOPAGO_WEBHOOK_SECRET)


def _headers() -> dict[str, str]:
    token = settings.MERCADOPAGO_ACCESS_TOKEN
    if not token:
        raise MercadoPagoErro("Mercado Pago não configurado")
    return {"Authorization": f"Bearer {token}"}


def criar_checkout(*, apoio_id: str, valor_centavos: int) -> tuple[str, str]:
    """Cria uma preferência de pagamento e devolve URL hospedada + preference id."""
    if not configurado() or valor_centavos not in VALORES_PERMITIDOS:
        raise MercadoPagoErro("Apoios indisponíveis")

    base_url = settings.APP_BASE_URL.rstrip("/")
    retorno = f"{base_url}/?apoio=retorno&apoio_id={apoio_id}"
    payload: dict[str, Any] = {
        "items": [{"title": "Apoio voluntário ao Dia de Missa", "quantity": 1, "currency_id": "BRL", "unit_price": float(Decimal(valor_centavos) / Decimal(100))}],
        "external_reference": apoio_id,
        "back_urls": {"success": retorno, "pending": retorno, "failure": retorno},
        "notification_url": f"{base_url}/api/v1/apoios/mercadopago/webhook",
        "metadata": {"apoio_id": apoio_id, "tipo": "apoio_voluntario"},
    }
    # A mesma referência precisa produzir a mesma preferência se houver retry de rede.
    headers = {**_headers(), "X-Idempotency-Key": apoio_id}
    try:
        resposta = httpx.post(CHECKOUT_PREFERENCES_URL, headers=headers, json=payload, timeout=15)
        resposta.raise_for_status()
        dados = resposta.json()
        checkout_url = dados.get("init_point")
        preference_id = dados.get("id")
    except (httpx.HTTPError, ValueError) as exc:
        raise MercadoPagoErro("Não foi possível iniciar o Checkout Pro") from exc

    checkout_host = urlparse(checkout_url).hostname if isinstance(checkout_url, str) else None
    host_confiavel = bool(checkout_host and (
        checkout_host in {"mercadopago.com", "mercadopago.com.br"}
        or checkout_host.endswith(".mercadopago.com")
        or checkout_host.endswith(".mercadopago.com.br")
    ))
    if not isinstance(checkout_url, str) or not checkout_url.startswith("https://") or not host_confiavel or not isinstance(preference_id, str):
        raise MercadoPagoErro("Resposta inválida do Checkout Pro")
    return checkout_url, preference_id


def validar_assinatura_webhook(*, x_signature: str | None, x_request_id: str | None, payment_id: str) -> bool:
    secret = settings.MERCADOPAGO_WEBHOOK_SECRET
    if not secret or not x_signature or not x_request_id:
        return False
    try:
        WebhookSignatureValidator.validate(x_signature, x_request_id, payment_id, secret)
    except InvalidWebhookSignatureError:
        return False
    return True


def consultar_pagamento(payment_id: str) -> dict[str, Any]:
    try:
        resposta = httpx.get(f"{PAYMENTS_URL}/{payment_id}", headers=_headers(), timeout=15)
        resposta.raise_for_status()
        dados = resposta.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise MercadoPagoErro("Não foi possível confirmar o pagamento") from exc
    if not isinstance(dados, dict):
        raise MercadoPagoErro("Resposta inválida de pagamento")
    return dados
