from __future__ import annotations

import os

from app.llm.base import LLMClient


def get_llm_client() -> LLMClient:
    """Devolve o cliente LLM conforme env LLM_PROVIDER (default: anthropic).

    Provedores suportados: 'anthropic', 'gemini', 'deepseek', 'openai'.
    Interface única (LLMClient.gerar), então o resto do pipeline não muda
    se você trocar de provedor.

    Para usar o Gemini Flash free (sem custo), basta:
      LLM_PROVIDER=gemini
      GEMINI_API_KEY=<chave do AI Studio>
      GEMINI_MODEL=gemini-3.6-flash

    Mantenha ANTHROPIC_API_KEY configurada (mesmo sem LLM_PROVIDER=anthropic)
    como fallback pago em emergências.
    """
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()

    if provider == "anthropic":
        from app.llm.anthropic_client import AnthropicClient
        return AnthropicClient()
    if provider == "gemini":
        from app.llm.gemini_client import GeminiClient
        return GeminiClient()
    if provider == "deepseek":
        from app.llm.deepseek import DeepSeekClient
        return DeepSeekClient()
    if provider == "openai":
        # Reaproveita o formato OpenAI-compatível do DeepSeekClient apontando
        # para a API da OpenAI seria possível, mas deixamos explícito o erro
        # até existir um OpenAIClient dedicado.
        raise NotImplementedError("OpenAIClient ainda não implementado")

    raise ValueError(f"LLM_PROVIDER desconhecido: {provider!r}")
