"""Reprocesso seguro de uma missa (backup + não-regressão).

Regra: só substituir a montagem existente se o reprocesso sair "concluido" no
gate. Se cair em pendente_revisao (gate/lexical/auditor reprovaram), RESTAURA o
backup dos blocos e mantém a montagem boa que já estava no ar.

Usado pela auto-atualização diária (missas futuras com pipeline_version antiga) e
por correções pontuais. Determinístico e sem raw SQL (tudo via ORM).
"""
from __future__ import annotations

import copy
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.missa import Missa as MissaModel, BlocoLiturgico

logger = logging.getLogger(__name__)


def snapshot_missa(db: Session, missa: MissaModel) -> dict:
    """Captura o estado restaurável da missa (blocos + campos de status)."""
    blocos = []
    for b in (
        db.query(BlocoLiturgico)
        .filter(BlocoLiturgico.missa_id == missa.id)
        .order_by(BlocoLiturgico.ordem)
        .all()
    ):
        blocos.append(
            {
                "ordem": b.ordem,
                "tipo": b.tipo,
                "titulo": b.titulo,
                "referencia": b.referencia,
                "conteudo": b.conteudo,
                "conteudo_formatado": b.conteudo_formatado,
                "conteudo_estruturado": copy.deepcopy(b.conteudo_estruturado),
                "observacoes": b.observacoes,
                "visivel": b.visivel,
            }
        )
    return {
        "status_processamento": missa.status_processamento,
        "observacoes": missa.observacoes,
        "pipeline_version": missa.pipeline_version,
        "revisao_json": copy.deepcopy(missa.revisao_json),
        "blocos": blocos,
    }


def restaurar_snapshot(db: Session, missa: MissaModel, snap: dict) -> None:
    """Restaura a missa exatamente ao estado do snapshot (blocos e status)."""
    db.query(BlocoLiturgico).filter(BlocoLiturgico.missa_id == missa.id).delete()
    for b in snap["blocos"]:
        db.add(BlocoLiturgico(missa_id=missa.id, **b))
    missa.status_processamento = snap["status_processamento"]
    missa.observacoes = snap["observacoes"]
    missa.pipeline_version = snap["pipeline_version"]
    missa.revisao_json = snap["revisao_json"]
    db.add(missa)
    db.commit()
    db.refresh(missa)


def reprocessar_com_seguranca(
    db: Session,
    missa: MissaModel,
    pdf_bytes: bytes,
    *,
    pdf_hash: Optional[str] = None,
) -> dict:
    """Reprocessa a missa a partir dos bytes do PDF, com não-regressão.

    Retorna {data, resultado, status, pipeline_version, motivo}. `resultado`:
      - "atualizado": reprocesso saiu concluido e substituiu a montagem;
      - "revertido": reprocesso caiu em pendente_revisao → backup restaurado;
      - "erro": exceção no reprocesso → backup restaurado.
    """
    from app.pipeline import processar_pdf
    from app.pipeline.download import hash_pdf
    from app.services.persist_missa import persistir_missa

    data_iso = missa.data.isoformat()
    snap = snapshot_missa(db, missa)
    versao_antes = snap["pipeline_version"]

    import tempfile
    import os as _os

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(pdf_bytes)
    tmp.close()
    try:
        missa_pyd = processar_pdf(tmp.name)
        nova = persistir_missa(
            db,
            missa_pyd,
            pdf_hash=pdf_hash or hash_pdf(pdf_bytes),
            fonte_url=settings.PDF_URL,
            pdf_bytes=pdf_bytes,
        )
        if nova.status_processamento == "concluido":
            logger.info(
                "auto-atualiza %s: %s -> %s (concluido)",
                data_iso, versao_antes, nova.pipeline_version,
            )
            return {
                "data": data_iso,
                "resultado": "atualizado",
                "status": nova.status_processamento,
                "pipeline_version": nova.pipeline_version,
                "motivo": None,
            }
        # Regressão: gate/lexical/auditor reprovaram — mantém a montagem boa.
        motivo = (nova.observacoes or "")[:200]
        restaurar_snapshot(db, missa, snap)
        logger.warning(
            "auto-atualiza %s: reprocesso saiu %s — REVERTIDO ao backup (%s)",
            data_iso, motivo, versao_antes,
        )
        return {
            "data": data_iso,
            "resultado": "revertido",
            "status": missa.status_processamento,
            "pipeline_version": missa.pipeline_version,
            "motivo": motivo,
        }
    except Exception as e:  # noqa: BLE001
        logger.exception("auto-atualiza %s: erro no reprocesso — restaurando backup", data_iso)
        try:
            db.rollback()
        except Exception:
            pass
        # Recarrega a missa e restaura (o rollback pode ter desfeito o delete).
        missa = db.query(MissaModel).filter(MissaModel.data == missa.data).first()
        try:
            restaurar_snapshot(db, missa, snap)
        except Exception:
            logger.exception("auto-atualiza %s: FALHA ao restaurar backup", data_iso)
        return {
            "data": data_iso,
            "resultado": "erro",
            "status": missa.status_processamento if missa else None,
            "pipeline_version": missa.pipeline_version if missa else None,
            "motivo": str(e)[:200],
        }
    finally:
        try:
            _os.unlink(tmp.name)
        except OSError:
            pass
