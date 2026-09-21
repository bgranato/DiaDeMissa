"""Contratos locais do transporte Gemini, sem chamar a API externa."""
from __future__ import annotations

import asyncio
import base64

import pytest

from app.llm.factory import get_llm_client
from app.llm.gemini_client import GeminiClient
from app.pipeline import montagem_convergente as loop


def test_factory_seleciona_gemini(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")

    assert isinstance(get_llm_client(), GeminiClient)


def test_gemini_direto_tem_precedencia_sobre_chave_openrouter(monkeypatch):
    chamadas: list[str] = []

    class _Direto:
        async def gerar(self, *_args, **_kwargs):
            chamadas.append("gemini-direto")
            return "ok"

    class _OpenRouter:
        async def gerar(self, *_args, **_kwargs):
            chamadas.append("openrouter")
            return "ok"

    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.6-flash")
    monkeypatch.setenv("OPENROUTER_API_KEY", "chave-legada")
    monkeypatch.setattr("app.llm.factory.get_llm_client", lambda: _Direto())
    monkeypatch.setattr("app.llm.openrouter_client.OpenRouterClient", lambda: _OpenRouter())

    assert asyncio.run(loop._gerar("mapa", "s", "u", b"%PDF-teste")) == "ok"
    assert chamadas == ["gemini-direto"]


def test_gemini_exige_chave(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY não configurada"):
        asyncio.run(GeminiClient().gerar("sistema", "pedido"))


def test_gemini_envia_pdf_e_retorna_texto(monkeypatch):
    import httpx
    from app.services import custo_llm_service

    capturado: dict = {}

    class _Resposta:
        status_code = 200

        def json(self):
            return {
                "candidates": [{"content": {"parts": [{"text": "{\"ok\": true}"}]}}],
                "usageMetadata": {"promptTokenCount": 12, "candidatesTokenCount": 4},
            }

    class _Cliente:
        def __init__(self, **kwargs):
            capturado["timeout"] = kwargs["timeout"]

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def post(self, url, **kwargs):
            capturado["url"] = url
            capturado.update(kwargs)
            return _Resposta()

    monkeypatch.setattr(httpx, "AsyncClient", _Cliente)
    monkeypatch.setattr(custo_llm_service, "registrar_custo_llm", lambda **_kwargs: None)
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.6-flash")

    resposta = asyncio.run(GeminiClient().gerar("sistema", "pedido", pdf_bytes=b"%PDF-teste"))

    assert resposta == '{"ok": true}'
    assert capturado["url"].endswith("/gemini-3.6-flash:generateContent")
    assert capturado["params"] == {"key": "chave-de-teste"}
    parte_pdf = capturado["json"]["contents"][0]["parts"][0]["inline_data"]
    assert parte_pdf == {
        "mime_type": "application/pdf",
        "data": base64.standard_b64encode(b"%PDF-teste").decode(),
    }
