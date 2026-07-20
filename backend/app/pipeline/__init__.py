import datetime
import logging
import os
from pathlib import Path
from typing import Union

from app.pipeline.extract import extrair_texto_estruturado
from app.pipeline.clean import limpar
from app.pipeline.download import obter_pdf
from app.schema.missa import Missa

logger = logging.getLogger(__name__)


def _usar_llm() -> bool:
    """Liga a estruturação por LLM via env USAR_LLM (1/true/yes/on)."""
    return os.getenv("USAR_LLM", "0").strip().lower() in ("1", "true", "yes", "on")


def _usar_llm_mm() -> bool:
    """Liga a montagem MULTIMODAL (PDF direto ao LLM) via USAR_LLM_MULTIMODAL."""
    return os.getenv("USAR_LLM_MULTIMODAL", "0").strip().lower() in ("1", "true", "yes", "on")


def processar_pdf(fonte: Union[str, Path, None] = None) -> Missa:
    if fonte is None:
        pdf_bytes = obter_pdf()
        texto_bruto = extrair_texto_estruturado(pdf_bytes)
    else:
        pdf_path = Path(fonte) if isinstance(fonte, str) else fonte
        pdf_bytes = pdf_path.read_bytes()
        texto_bruto = extrair_texto_estruturado(pdf_path)

    texto_limpo = limpar(texto_bruto)

    # Etapa 4 — estruturação.
    # USAR_LLM_MULTIMODAL=1: manda o PDF direto ao LLM (fonte da verdade) — elimina
    # a classe de erros de extração/regex na origem. Cai no caminho de texto e depois
    # no regex se falhar, então é seguro.
    if _usar_llm_mm():
        logger.info("Estruturação: LLM MULTIMODAL (PDF direto)")
        from app.pipeline.structure_llm import estruturar_via_llm_mm
        return estruturar_via_llm_mm(pdf_bytes, texto_limpo)

    # Com USAR_LLM=1: usa o LLM (entende o documento → corrige a classe inteira
    # de erros do regex). O próprio estruturar_via_llm já cai no regex como
    # fallback se o LLM falhar/estiver sem chave, então a flag é segura.
    if _usar_llm():
        logger.info("Estruturação: LLM (USAR_LLM ativo)")
        from app.pipeline.structure_llm import estruturar_via_llm
        return estruturar_via_llm(texto_limpo)

    logger.info("Estruturação: regex (USAR_LLM inativo)")
    from app.pipeline.structure import estruturar
    return estruturar(texto_limpo)
