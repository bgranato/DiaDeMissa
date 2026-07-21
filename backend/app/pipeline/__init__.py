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
        missa = estruturar_via_llm_mm(pdf_bytes, texto_limpo)
    elif _usar_llm():
        # Com USAR_LLM=1: usa o LLM (entende o documento → corrige a classe inteira
        # de erros do regex). O próprio estruturar_via_llm já cai no regex como
        # fallback se o LLM falhar/estiver sem chave, então a flag é segura.
        logger.info("Estruturação: LLM (USAR_LLM ativo)")
        from app.pipeline.structure_llm import estruturar_via_llm
        missa = estruturar_via_llm(texto_limpo)
    else:
        logger.info("Estruturação: regex (USAR_LLM inativo)")
        from app.pipeline.structure import estruturar
        missa = estruturar(texto_limpo)

    _verificar_lexico(missa, texto_limpo)
    return missa


def _verificar_lexico(missa, texto_limpo: str) -> None:
    """Camada determinística entre montagem e gate: toda palavra do texto litúrgico
    da montagem deve existir no vocabulário do texto-fonte. Palavra ausente = suspeita
    de typo do LLM. Marca `observacoes` com "[lexical] palavras fora do fonte: …".
    O persist_missa decide (bloquear → pendente_revisao, ou alertar → e-mail)."""
    try:
        from app.services.verificador_lexical import ativo, verificar_lexico, resumo, MARCA_LEXICAL
        if not ativo():
            return
        blocos = [b.model_dump() for b in (missa.blocos or [])]
        sus = verificar_lexico(texto_limpo, blocos, getattr(missa, "descricao", None))
        if not sus:
            return
        for s in sus:
            logger.warning("[lexical] %s (%s): '%s' — …%s…", s["bloco"], s["campo"], s["palavra"], s["contexto"])
        marca = MARCA_LEXICAL + resumo(sus)
        obs = getattr(missa, "observacoes", None) or ""
        missa.observacoes = marca + (f" · {obs}" if obs else "")
    except Exception:
        logger.exception("Verificador léxico falhou (não bloqueante)")
