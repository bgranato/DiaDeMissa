from __future__ import annotations

from abc import ABC, abstractmethod


class LLMClient(ABC):
    @abstractmethod
    async def gerar(self, system_prompt: str, user_prompt: str) -> str:
        ...
