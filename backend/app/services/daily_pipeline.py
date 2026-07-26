"""Job diário: baixar PDF → parsear → persistir missa estruturada no BD."""
from __future__ import annotations

import logging
import tempfile
from datetime import date
from pathlib import Path
from typing import Optional

from app.core.database import SessionLocal
from app.core.config import settings
from app.core.pipeline_version import pipeline_version
from app.models.missa import Missa as MissaModel
from app.pipeline import processar_pdf
from app.pipeline.download import obter_pdf, hash_pdf, CACHE_DIR
from app.services.persist_missa import persistir_missa

logger = logging.getLogger(__name__)


def selecionar_para_reprocesso(db, hoje: date) -> list[MissaModel]:
    """Missas com data >= hoje cuja pipeline_version difere da atual (ou é null).

    São as missas montadas por uma versão ANTIGA das regras — candidatas a
    reprocesso automático. Só entram as que estão no ar (concluido): não mexe
    em pendente_revisao (já sob revisão humana)."""
    alvo = pipeline_version()
    candidatas = (
        db.query(MissaModel)
        .filter(MissaModel.data >= hoje, MissaModel.status_processamento == "concluido")
        .order_by(MissaModel.data.asc())
        .all()
    )
    return [m for m in candidatas if (m.pipeline_version or "") != alvo]


def auto_atualizar_montagens(db, hoje: Optional[date] = None) -> dict:
    """Varre missas futuras montadas por versão antiga e reprocessa com segurança.

    Só reprocessa quem tem PDF arquivado (CACHE_DIR/archive/<data>.pdf). Cada
    reprocesso é não-regressivo: se cair em pendente_revisao, restaura o backup
    e mantém a montagem boa. Idempotente: após atualizar, a missa passa a ter a
    versão atual e não é mais selecionada."""
    from app.services.reprocesso_seguro import reprocessar_com_seguranca

    hoje = hoje or date.today()
    alvos = selecionar_para_reprocesso(db, hoje)
    resultados = []
    for m in alvos:
        pdf_path = CACHE_DIR / "archive" / f"{m.data.isoformat()}.pdf"
        if not pdf_path.exists():
            logger.info("auto-atualiza %s: sem PDF arquivado — pulando", m.data)
            resultados.append({"data": m.data.isoformat(), "resultado": "sem_pdf"})
            continue
        try:
            pdf_bytes = pdf_path.read_bytes()
        except OSError as e:
            logger.warning("auto-atualiza %s: erro lendo PDF (%s)", m.data, e)
            resultados.append({"data": m.data.isoformat(), "resultado": "sem_pdf"})
            continue
        resultados.append(reprocessar_com_seguranca(db, m, pdf_bytes))
    resumo = {
        "alvo_pipeline_version": pipeline_version(),
        "selecionadas": len(alvos),
        "atualizadas": sum(1 for r in resultados if r.get("resultado") == "atualizado"),
        "revertidas": sum(1 for r in resultados if r.get("resultado") == "revertido"),
        "sem_pdf": sum(1 for r in resultados if r.get("resultado") == "sem_pdf"),
        "erros": sum(1 for r in resultados if r.get("resultado") == "erro"),
        "detalhes": resultados,
    }
    if alvos:
        logger.info("auto-atualiza montagens: %s", {k: v for k, v in resumo.items() if k != "detalhes"})
    return resumo


def executar_pipeline_diario(forcar: bool = False) -> dict:
    """Download → parse → persist. Idempotente via hash do PDF.

    Args:
        forcar: se True, reprocessa mesmo com hash idêntico.
    Returns:
        dict com {status, missa_id, data, hash, motivo}

    Robustez: se o cache em disco falhar (filesystem read-only, sem espaço, etc),
    processa via tempfile em vez de propagar o erro. O cache é otimização; o
    crítico é a missa chegar no BD — não deve falhar silenciosamente nunca mais.
    """
    logger.info("Iniciando pipeline diário (forcar=%s)", forcar)

    try:
        conteudo = obter_pdf()
    except Exception as e:
        logger.exception("Falha no download do PDF")
        return {"status": "erro_download", "motivo": str(e)}

    h = hash_pdf(conteudo)
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        pdf_path = CACHE_DIR / f"{h}.pdf"
        if not pdf_path.exists():
            pdf_path.write_bytes(conteudo)
    except (OSError, PermissionError) as e:
        logger.warning(
            "Cache em %s indisponível (%s) — fallback pra tempfile, missa será processada igual",
            CACHE_DIR, e,
        )
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.write(conteudo)
        tmp.close()
        pdf_path = Path(tmp.name)

    db = SessionLocal()
    try:
        if not forcar:
            existente = db.query(MissaModel).filter(MissaModel.pdf_hash == h).first()
            if existente:
                logger.info("PDF não alterado (hash %s). Missa id=%s já no BD.", h[:8], existente.id)
                # Mesmo sem folheto novo, varre missas futuras montadas por versão
                # antiga e atualiza (a evolução do pipeline não pode deixar buracos).
                auto = auto_atualizar_montagens(db)
                return {
                    "status": "ignorado",
                    "motivo": "hash inalterado",
                    "missa_id": existente.id,
                    "hash": h,
                    "auto_atualizacao": auto,
                }

        missa_pyd = processar_pdf(pdf_path)
        missa_db = persistir_missa(
            db, missa_pyd, pdf_hash=h, fonte_url=settings.PDF_URL, pdf_bytes=conteudo,
        )
        logger.info(
            "Missa persistida id=%s data=%s blocos=%d",
            missa_db.id, missa_db.data, len(missa_db.blocos),
        )
        # Arquivo permanente nomeado por data — fácil de localizar/auditar/reprocessar
        # depois. CACHE_DIR/archive/YYYY-MM-DD.pdf. Substitui se já existir (PDF
        # atualizado durante o dia, ex: errata Arquidiocese).
        try:
            archive_dir = CACHE_DIR / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_path = archive_dir / f"{missa_db.data.isoformat()}.pdf"
            archive_path.write_bytes(conteudo)
        except (OSError, PermissionError) as e:
            logger.warning("Falha ao arquivar PDF por data (%s) — segue sem bloqueio", e)
        # Após processar o folheto do dia, atualiza missas futuras montadas por
        # versão antiga do pipeline (elimina o "vão" entre reprocesso do histórico
        # e regras novas). Não-regressivo: só substitui se sair concluido.
        auto = auto_atualizar_montagens(db)
        return {
            "status": "ok",
            "missa_id": missa_db.id,
            "data": missa_db.data.isoformat(),
            "hash": h,
            "blocos": len(missa_db.blocos),
            "auto_atualizacao": auto,
        }
    except Exception as e:
        logger.exception("Falha no parsing/persistência")
        db.rollback()
        return {"status": "erro_parse", "motivo": str(e), "hash": h}
    finally:
        db.close()
