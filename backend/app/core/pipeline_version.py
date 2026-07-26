"""Versão da montagem litúrgica (pipeline_version).

Identifica a versão das REGRAS que produzem a montagem, para que missas
persistidas por uma versão antiga do pipeline possam ser detectadas e
reprocessadas automaticamente quando as regras evoluem.

A versão é `<hash8>+<modelo>`, onde `hash8` é o SHA-256 (8 primeiros hex) do
conteúdo concatenado dos arquivos que determinam a montagem (prompts, estrutura,
limpeza, verificador léxico) e `modelo` é o modelo multimodal em uso
(ANTHROPIC_MODEL_MM). Assim, qualquer mudança nas regras OU no modelo muda a
versão — exatamente o gatilho de "precisa reprocessar".

Determinístico e sem dependência de git no runtime (funciona em deploy que não
seja um checkout). Calculado uma vez e cacheado por processo.
"""
from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from pathlib import Path

# Arquivos cujo conteúdo define a montagem. Ordem fixa (o hash depende dela).
_BACKEND = Path(__file__).resolve().parent.parent.parent
_ARQUIVOS_REGRA = [
    "app/llm/prompts.py",
    "app/pipeline/structure_llm.py",
    "app/pipeline/clean.py",
    "app/services/verificador_lexical.py",
]


def _modelo_montagem() -> str:
    """Modelo multimodal em uso (mesma resolução do pipeline LLM)."""
    return (
        os.getenv("ANTHROPIC_MODEL_MM")
        or os.getenv("ANTHROPIC_MODEL")
        or "haiku-default"
    )


@lru_cache(maxsize=1)
def _hash_regras() -> str:
    h = hashlib.sha256()
    for rel in _ARQUIVOS_REGRA:
        caminho = _BACKEND / rel
        try:
            h.update(caminho.read_bytes())
        except OSError:
            # Se um arquivo sumir, ainda produzimos uma versão estável (marca ausência).
            h.update(f"<ausente:{rel}>".encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:8]


def pipeline_version() -> str:
    """Versão atual da montagem: `<hash8-regras>+<modelo>`.

    Não cacheia o modelo (pode mudar por env entre processos), mas cacheia o
    hash dos arquivos (imutáveis no processo)."""
    return f"{_hash_regras()}+{_modelo_montagem()}"
