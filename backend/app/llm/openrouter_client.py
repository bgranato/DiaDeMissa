"""Cliente OpenRouter (OpenAI-compatível) para modelos de família diferente
(ex.: Gemini Flash) no mapa (passo 3) e no conferente (passo 6).

Dormente sem OPENROUTER_API_KEY — só é usado quando MODELO_MAPA/MODELO_CONFERENTE
apontam para um modelo Gemini/Google E a chave existe (ver montagem_convergente).
"""
from __future__ import annotations

import base64
import os
from typing import Optional

from app.llm.base import LLMClient


class OpenRouterClient(LLMClient):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.model = model or os.getenv("MODELO_MAPA", "google/gemini-2.0-flash-001")

    async def gerar(self, system_prompt: str, user_prompt: str,
                    pdf_bytes: "bytes | None" = None, model: "str | None" = None) -> str:
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY não configurada")
        import httpx

        modelo = model or self.model
        if pdf_bytes:
            data_url = "data:application/pdf;base64," + base64.standard_b64encode(pdf_bytes).decode()
            user_content = [
                {"type": "file", "file": {"filename": "folheto.pdf", "file_data": data_url}},
                {"type": "text", "text": user_prompt},
            ]
        else:
            user_content = user_prompt
        payload = {
            "model": modelo,
            "max_tokens": int(os.getenv("OPENROUTER_MAX_TOKENS", "32000")),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "content-type": "application/json"}
        _timeout = float(os.getenv("OPENROUTER_HTTP_TIMEOUT", "600"))
        async with httpx.AsyncClient(timeout=_timeout) as client:
            resp = await client.post("https://openrouter.ai/api/v1/chat/completions",
                                     headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            u = data.get("usage") or {}
            if u:
                ent = u.get("prompt_tokens", 0); sai = u.get("completion_tokens", 0)
                try:
                    from app.services.custo_llm_service import registrar_custo_llm
                    # preço aproximado do Gemini Flash; ajuste se trocar de modelo
                    custo = ent/1e6*0.10 + sai/1e6*0.40
                    print(f"[LLM] {modelo} · entrada={ent} tok · saída={sai} tok · ~US$ {custo:.4f}")
                    registrar_custo_llm(modelo, ent, sai, custo)
                except Exception:
                    pass
            return (data["choices"][0]["message"]["content"] or "").strip()
