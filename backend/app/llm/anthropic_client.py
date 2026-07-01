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

    async def gerar(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY não configurada")
        import httpx

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            # Folheto completo gera JSON grande; 8192 truncava no meio (JSON inválido).
            # 16384 cobre folhetos longos com folga. Trocável via env ANTHROPIC_MAX_TOKENS.
            "max_tokens": int(os.getenv("ANTHROPIC_MAX_TOKENS", "16384")),
            "temperature": 0.0,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            # Log de uso (tokens) para acompanhar o custo por folheto.
            u = data.get("usage") or {}
            if u:
                ent, sai = u.get("input_tokens", 0), u.get("output_tokens", 0)
                # Haiku 4.5: $1/1M entrada, $5/1M saída (ajuste se trocar de modelo).
                custo = ent / 1e6 * 1.0 + sai / 1e6 * 5.0
                print(f"[LLM] {self.model} · entrada={ent} tok · saída={sai} tok · ~US$ {custo:.4f}")
                # Persiste o custo para o painel admin (best-effort, não bloqueia).
                try:
                    from app.services.custo_llm_service import registrar_custo_llm
                    registrar_custo_llm(self.model, ent, sai, custo)
                except Exception:
                    pass
            # content é uma lista de blocos; juntamos o texto.
            partes = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
            return "".join(partes).strip()
