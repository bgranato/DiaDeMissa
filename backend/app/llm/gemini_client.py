"""Cliente Google Gemini (Google AI Studio / Generative Language API).

Sem custo no free tier do AI Studio — usado como substituto do Anthropic/OpenRouter
para a montagem multimodal de folhetos litúrgicos em PT-BR. O Gauntlet Loop fica
intacto: o cliente só troca o transporte HTTP; o resto do pipeline (mapa, montagem,
conferente Celular, conferente Celebrante, cobertura palavra-a-palavra) continua
idêntico.

Config via env:
  GEMINI_API_KEY            — obrigatória (https://aistudio.google.com/app/apikey, free)
  GEMINI_MODEL              — opcional (default: gemini-3.6-flash)
  GEMINI_MAX_TOKENS         — opcional (default: 8192)
  GEMINI_HTTP_TIMEOUT       — opcional (default: 600s)

Endpoint: ``https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent``
Multimodal PDF: passa como ``inline_data`` com mime_type ``application/pdf`` (≤ 50 MB).
Limites do free tier (2026-09): 5-15 RPM, 20-1500 RPD por modelo. Folheto Arqrio
inteiro (~30 páginas, ~1 MB) cabe de sobra.

Trade-offs assumidos:
- Google pode treinar com inputs fora de UE/Reino Unido. O folheto é público
  (Arquidiocese do Rio), então o risco é baixo — vale registrar.
- Catálogo gratuito pode rotacionar: em 2026-09 o snapshot estável do free tier
  é ``gemini-3.6-flash`` (``gemini-2.0-flash`` foi aposentado — ver validação
  no relatório ``2026-09-20_22-15_cliente-gemini-implementado.md``). Manter
  ``ANTHROPIC_API_KEY`` configurada como fallback pago (desligar quando não
  quiser gastar).
"""
from __future__ import annotations

import base64
import os
from typing import Optional

from app.llm.base import LLMClient


class GeminiClient(LLMClient):
    """Cliente Gemini direto (Google AI Studio) — multimodal, sem custo no free tier."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        # gemini-3.6-flash é o snapshot estável do free tier em 2026-09 (gemini-2.0-flash
        # foi aposentado — verificado em validação 2026-09-20). Suporta multimodal
        # nativo (PDF inline), 1M tokens de contexto, output 8k.
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

    async def gerar(self, system_prompt: str, user_prompt: str,
                    pdf_bytes: "bytes | None" = None, model: "str | None" = None,
                    contexto: str = "montagem_folheto", referencia: "str | None" = None) -> str:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY não configurada (https://aistudio.google.com/app/apikey)")
        import httpx

        modelo = model or self.model
        # Gemini usa ``systemInstruction`` separado (system role ≠ user role).
        # Multimodal: PDF como inline_data (≤ 20 MB inline; Files API para maior).
        # O folheto Arqrio tem ~1 MB, então inline é suficiente.
        parts: list[dict] = []
        if pdf_bytes:
            parts.append({
                "inline_data": {
                    "mime_type": "application/pdf",
                    "data": base64.standard_b64encode(pdf_bytes).decode(),
                }
            })
        parts.append({"text": user_prompt})

        payload: dict = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "maxOutputTokens": int(os.getenv("GEMINI_MAX_TOKENS", "8192")),
                "temperature": 0.0,
            },
        }
        # responseMimeType=application/json força o Gemini a devolver JSON puro,
        # mas os prompts do pipeline já pedem JSON explícito. Mantemos texto puro
        # para preservar o contrato com `_extrair_json()` em
        # `montagem_convergente.py` (que faz parse tolerante a cercas markdown).

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
        _timeout = float(os.getenv("GEMINI_HTTP_TIMEOUT", "600"))
        async with httpx.AsyncClient(timeout=_timeout) as client:
            resp = await client.post(
                url,
                params={"key": self.api_key},
                headers={"content-type": "application/json"},
                json=payload,
            )
            if resp.status_code >= 400:
                corpo = resp.text[:600]
                raise httpx.HTTPStatusError(
                    f"{resp.status_code} — {corpo}", request=resp.request, response=resp,
                )
            data = resp.json()

        # Extrai texto de candidates[0].content.parts[*].text
        try:
            candidato = data["candidates"][0]
            partes = candidato["content"]["parts"]
            texto = "".join(p.get("text", "") for p in partes if "text" in p)
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Resposta Gemini em formato inesperado: {data!r}") from e

        # Registra uso (free tier = custo $0; mantém histórico para auditoria).
        u = data.get("usageMetadata") or {}
        ent = int(u.get("promptTokenCount", 0))
        sai = int(u.get("candidatesTokenCount", 0))
        try:
            from app.services.custo_llm_service import registrar_custo_llm
            custo = 0.0  # free tier
            print(f"[LLM] {modelo} (free) · entrada={ent} tok · saída={sai} tok · US$ 0.0000")
            registrar_custo_llm(modelo, ent, sai, custo, contexto=contexto, referencia=referencia)
        except Exception:
            pass

        return texto.strip()
