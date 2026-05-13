"""Persistência da Missa estruturada (Pydantic) no banco.

Faz a ponte entre o output do pipeline (app/pipeline/processar_pdf) e os
models SQLAlchemy. Cada bloco do Pydantic é serializado em JSON na coluna
`conteudo_estruturado` do BlocoLiturgico, preservando a estrutura rica
(turnos, refrão, versículos, etc.) que o frontend espera.
"""
from __future__ import annotations

from datetime import date as _date
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.missa import Missa as MissaModel, BlocoLiturgico
from app.schema.missa import Missa as MissaSchema


def _parse_data(data_str: str) -> _date:
    return _date.fromisoformat(data_str)


def persistir_missa(
    db: Session,
    missa_pydantic: MissaSchema,
    *,
    pdf_hash: Optional[str] = None,
    fonte_url: Optional[str] = None,
) -> MissaModel:
    """Upsert a missa estruturada no BD. Substitui blocos existentes."""
    data = _parse_data(missa_pydantic.data)
    existente = db.query(MissaModel).filter(MissaModel.data == data).first()

    payload = dict(
        data=data,
        celebracao=missa_pydantic.titulo_celebracao,
        subtitulo=None,
        descricao=missa_pydantic.descricao,
        tempo_liturgico=None,
        ano_liturgico=missa_pydantic.ano_liturgico,
        categoria=missa_pydantic.categoria,
        observacoes=missa_pydantic.observacoes,
        creditos_cantos=missa_pydantic.creditos_cantos.model_dump() if missa_pydantic.creditos_cantos else None,
        palavra_do_dia=missa_pydantic.palavra_do_dia.model_dump() if missa_pydantic.palavra_do_dia else None,
        fonte_pdf_url=fonte_url or settings.PDF_URL,
        pdf_hash=pdf_hash,
        status_processamento="concluido",
    )

    if existente:
        for key, value in payload.items():
            setattr(existente, key, value)
        db.query(BlocoLiturgico).filter(BlocoLiturgico.missa_id == existente.id).delete()
        missa = existente
    else:
        missa = MissaModel(**payload)
        db.add(missa)
        db.flush()

    for bloco in missa_pydantic.blocos:
        bloco_dict = bloco.model_dump()
        db.add(
            BlocoLiturgico(
                missa_id=missa.id,
                ordem=bloco.ordem,
                tipo=bloco_dict.get("tipo", "oracao"),
                titulo=bloco.titulo,
                referencia=bloco_dict.get("referencia"),
                conteudo=None,
                conteudo_formatado=None,
                conteudo_estruturado=bloco_dict,
                visivel=True,
            )
        )

    db.commit()
    db.refresh(missa)
    return missa


def reconstruir_missa(missa_db: MissaModel) -> dict:
    """Reconstrói o dict que o frontend espera (formato Pydantic Missa) a partir do BD."""
    blocos = [b.conteudo_estruturado for b in missa_db.blocos if b.conteudo_estruturado]
    return {
        "data": missa_db.data.isoformat() if missa_db.data else None,
        "ano_liturgico": missa_db.ano_liturgico,
        "titulo_celebracao": missa_db.celebracao,
        "categoria": missa_db.categoria,
        "descricao": missa_db.descricao,
        "observacoes": missa_db.observacoes,
        "creditos_cantos": missa_db.creditos_cantos or {},
        "palavra_do_dia": missa_db.palavra_do_dia,
        "blocos": blocos,
    }
