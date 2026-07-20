from __future__ import annotations

from abc import ABC, abstractmethod


class LLMClient(ABC):
    @abstractmethod
    async def gerar(
        self, system_prompt: str, user_prompt: str,
        pdf_bytes: "bytes | None" = None, model: "str | None" = None,
    ) -> str:
        """Gera a resposta. Se `pdf_bytes` for dado, envia o PDF ao modelo
        (multimodal) além do texto — a montagem lê o folheto direto da fonte."""
        ...
