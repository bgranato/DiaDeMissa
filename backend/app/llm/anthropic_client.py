from __future__ import annotations

import os
from typing import Optional

from app.llm.base import LLMClient


class AnthropicClient(LLMClient):
    """Cliente Anthropic (Claude) seguindo a interface LLMClient do projeto.

    Usa a Messages API. O system prompt vai no campo `system` (não como mensagem),
    como recomenda a Anthropic. Temperatura baixa pra extração determinística.

    Config via env:
      ANTHROPIC_API_KEY  — obrigatória
      ANTHROPIC_MODEL     — opcional (default: claude-sonnet-4-6)
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        # Haiku por padrão: ~3x mais barato que o Sonnet e suficiente para a
        # extração estruturada do folheto. Trocável via env ANTHROPIC_MODEL
        # (ex.: "claude-sonnet-4-6" se quiser mais qualidade).
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

    async def gerar(self, system_prompt: str, user_prompt: str,
                    pdf_bytes: "bytes | None" = None, model: "str | None" = None) -> str:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY não configurada")
        import httpx

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        # Multimodal: manda o PDF como fonte da verdade + o texto como conteúdo.
        # Permite trocar o modelo só na leitura do PDF via ANTHROPIC_MODEL_MM.
        if pdf_bytes:
            import base64
            modelo = model or os.getenv("ANTHROPIC_MODEL_MM", self.model)
            content = [
                {"type": "document", "source": {
                    "type": "base64", "media_type": "application/pdf",
                    "data": base64.standard_b64encode(pdf_bytes).decode(),
                }},
                {"type": "text", "text": user_prompt},
            ]
        else:
            modelo = model or self.model
            content = user_prompt
        # Folheto completo gera JSON grande; missas longas (hino jubilar + OE IV)
        # passam de 32k tokens de saída. 64000 dá folga (Sonnet 5 suporta 128k).
        # Trocável via env ANTHROPIC_MAX_TOKENS.
        max_tokens = int(os.getenv("ANTHROPIC_MAX_TOKENS", "64000"))
        payload = {
            "model": modelo,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": content},
            ],
        }
        # `temperature` é deprecado em alguns modelos novos (ex.: sonnet-5). Só
        # envia onde é aceito (ex.: haiku-4-5) para não tomar 400.
        if not any(x in modelo for x in ("sonnet-5", "opus-4")):
            payload["temperature"] = 0.0
        # A Messages API EXIGE streaming quando max_tokens é grande (senão 400
        # "Streaming is required…"). Acima de ~21k tokens, streamamos e acumulamos
        # os deltas — evita o 400 e permite montagens completas de missas longas.
        usar_stream = max_tokens > 20000
        # Timeout generoso: geração de missas longas pode passar de 3 min; 180s
        # dava httpx.ReadTimeout → fallback=texto.
        _timeout = float(os.getenv("ANTHROPIC_HTTP_TIMEOUT", "600"))

        def _log_uso(ent: int, sai: int) -> None:
            _preco = {"haiku": (1.0, 5.0), "sonnet": (3.0, 15.0), "opus": (15.0, 75.0)}
            pin, pout = next((v for k, v in _preco.items() if k in modelo), (1.0, 5.0))
            custo = ent / 1e6 * pin + sai / 1e6 * pout
            print(f"[LLM] {modelo} · entrada={ent} tok · saída={sai} tok · ~US$ {custo:.4f}")
            try:
                from app.services.custo_llm_service import registrar_custo_llm
                registrar_custo_llm(modelo, ent, sai, custo)
            except Exception:
                pass

        async with httpx.AsyncClient(timeout=_timeout) as client:
            if not usar_stream:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                u = data.get("usage") or {}
                if u:
                    _log_uso(u.get("input_tokens", 0), u.get("output_tokens", 0))
                partes = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
                return "".join(partes).strip()

            # --- Streaming (SSE): acumula os text_delta ---
            import json as _json
            payload["stream"] = True
            partes: list[str] = []
            ent = sai = 0
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                if resp.status_code >= 400:
                    corpo = (await resp.aread()).decode("utf-8", "replace")
                    raise httpx.HTTPStatusError(
                        f"{resp.status_code} — {corpo[:400]}", request=resp.request, response=resp,
                    )
                async for linha in resp.aiter_lines():
                    if not linha or not linha.startswith("data:"):
                        continue
                    dado = linha[5:].strip()
                    if not dado or dado == "[DONE]":
                        continue
                    try:
                        ev = _json.loads(dado)
                    except ValueError:
                        continue
                    t = ev.get("type")
                    if t == "content_block_delta":
                        d = ev.get("delta") or {}
                        if d.get("type") == "text_delta":
                            partes.append(d.get("text", ""))
                    elif t == "message_start":
                        ent = ((ev.get("message") or {}).get("usage") or {}).get("input_tokens", 0)
                    elif t == "message_delta":
                        sai = (ev.get("usage") or {}).get("output_tokens", sai)
            if ent or sai:
                _log_uso(ent, sai)
            return "".join(partes).strip()
