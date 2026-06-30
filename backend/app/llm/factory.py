from __future__ import annotations

import os

from app.llm.base import LLMClient


def get_llm_client() -> LLMClient:
    """Devolve o cliente LLM conforme env LLM_PROVIDER (default: anthropic).

    Provedores suportados: 'anthropic', 'deepseek', 'openai'.
    Interface única (LLMClient.gerar), então o resto do pipeline não muda
    se você trocar de provedor.
    """
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()

    if provider == "anthropic":
        from app.llm.anthropic_client import AnthropicClient
        return AnthropicClient()
    if provider == "deepseek":
        from app.llm.deepseek import DeepSeekClient
        return DeepSeekClient()
    if provider == "openai":
        # Reaproveita o formato OpenAI-compatível do DeepSeekClient apontando
        # para a API da OpenAI seria possível, mas deixamos explícito o erro
        # até existir um OpenAIClient dedicado.
        raise NotImplementedError("OpenAIClient ainda não implementado")

    raise ValueError(f"LLM_PROVIDER desconhecido: {provider!r}")
