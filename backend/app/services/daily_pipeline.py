"""Job diário: baixar PDF → parsear → persistir missa estruturada no BD."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.core.database import SessionLocal
from app.core.config import settings
from app.models.missa import Missa as MissaModel
from app.pipeline import processar_pdf
from app.pipeline.download import obter_pdf, hash_pdf, CACHE_DIR
from app.services.persist_missa import persistir_missa

logger = logging.getLogger(__name__)


def executar_pipeline_diario(forcar: bool = False) -> dict:
    """Download → parse → persist. Idempotente via hash do PDF.

    Args:
        forcar: se True, reprocessa mesmo com hash idêntico.
    Returns:
        dict com {status, missa_id, data, hash, motivo}
    """
    logger.info("Iniciando pipeline diário (forcar=%s)", forcar)

    try:
        conteudo = obter_pdf()
    except Exception as e:
        logger.exception("Falha no download do PDF")
        return {"status": "erro_download", "motivo": str(e)}

    h = hash_pdf(conteudo)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = CACHE_DIR / f"{h}.pdf"
    if not pdf_path.exists():
        pdf_path.write_bytes(conteudo)

    db = SessionLocal()
    try:
        if not forcar:
            existente = db.query(MissaModel).filter(MissaModel.pdf_hash == h).first()
            if existente:
                logger.info("PDF não alterado (hash %s). Missa id=%s já no BD.", h[:8], existente.id)
                return {
                    "status": "ignorado",
                    "motivo": "hash inalterado",
                    "missa_id": existente.id,
                    "hash": h,
                }

        missa_pyd = processar_pdf(pdf_path)
        missa_db = persistir_missa(
            db, missa_pyd, pdf_hash=h, fonte_url=settings.PDF_URL,
        )
        logger.info(
            "Missa persistida id=%s data=%s blocos=%d",
            missa_db.id, missa_db.data, len(missa_db.blocos),
        )
        return {
            "status": "ok",
            "missa_id": missa_db.id,
            "data": missa_db.data.isoformat(),
            "hash": h,
            "blocos": len(missa_db.blocos),
        }
    except Exception as e:
        logger.exception("Falha no parsing/persistência")
        db.rollback()
        return {"status": "erro_parse", "motivo": str(e), "hash": h}
    finally:
        db.close()
