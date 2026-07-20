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
    pdf_bytes: Optional[bytes] = None,
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

    # Fallback barulhento: se a montagem caiu no REGEX (pior caminho), o
    # structure_llm gravou "[pipeline] fallback=regex" em observacoes. Nesse caso
    # a missa vai para pendente_revisao (esconde do fiel até revisão).
    try:
        if "[pipeline] fallback=regex" in (missa.observacoes or ""):
            import logging
            missa.status_processamento = "pendente_revisao"
            db.add(missa)
            db.commit()
            db.refresh(missa)
            logging.getLogger(__name__).warning(
                "Missa %s montada por REGEX (fallback) — pendente_revisao", missa.data
            )
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Falha ao checar fallback %s", missa.data)

    # Compare-and-commit: auditoria síncrona pós-persistência.
    # Critérios CRÍTICOS marcam pendente_revisao (escondem do app até revisão).
    try:
        import logging
        from app.services.auditor_missa import auditar_missa
        rel = auditar_missa(missa)
        if rel.tem_critica:
            missa.status_processamento = "pendente_revisao"
            db.add(missa)
            db.commit()
            db.refresh(missa)
            logging.getLogger(__name__).warning(
                "Missa %s (PDF) marcada pendente_revisao — %d crítico(s)",
                missa.data,
                sum(1 for a in rel.achados if a.severidade == "CRÍTICA"),
            )
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "Falha ao auditar missa %s (não bloqueante)", missa.data
        )

    # GATE PDF (pilar 2): um 2º modelo (Sonnet) confere a montagem contra o PDF
    # OFICIAL. Divergência CRÍTICA (ref/rubrica/texto) → pendente_revisao. Precisa
    # dos bytes do PDF + USAR_GATE_PDF=1. Fail-open dentro do auditar_contra_pdf.
    try:
        from app.services.auditor_folheto import usar_gate_pdf, auditar_contra_pdf
        if pdf_bytes and usar_gate_pdf() and missa.status_processamento == "concluido":
            import logging
            rel_pdf = auditar_contra_pdf(missa, pdf_bytes)
            # Guarda o resultado do gate para o admin revisar (diff PDF×montagem).
            missa.revisao_json = {
                "ok": rel_pdf.get("ok"),
                "criticas": rel_pdf.get("criticas", []),
                "todas": rel_pdf.get("todas", []),
            }
            db.add(missa)
            db.commit()
            db.refresh(missa)
            if not rel_pdf["ok"]:
                missa.status_processamento = "pendente_revisao"
                db.add(missa)
                db.commit()
                db.refresh(missa)
                logging.getLogger(__name__).warning(
                    "GATE PDF: missa %s -> pendente_revisao (%d crítica(s)): %s",
                    missa.data, len(rel_pdf["criticas"]),
                    "; ".join(str(c.get("detalhe") or c.get("esperado_pdf")) for c in rel_pdf["criticas"])[:500],
                )
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "Gate PDF falhou (não bloqueante) %s", missa.data
        )

    # Alerta por e-mail "missa disponível" — 1x por missa, só se publicada (concluido).
    try:
        if missa.status_processamento == "concluido":
            from app.services.notif_missa_disponivel import notificar_missa_disponivel
            notificar_missa_disponivel(db, missa)
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "Falha ao notificar 'missa disponível' %s (não bloqueante)", missa.data
        )

    return missa


def reconstruir_missa(missa_db: MissaModel) -> dict:
    """Reconstrói o dict que o frontend espera (formato Pydantic Missa) a partir do BD.

    Suporta duas origens de bloco:
    1. Blocos do pipeline antigo (PDF Arquidiocese) → têm `conteudo_estruturado` preenchido.
    2. Blocos da liturgia diária CNBB/Canção Nova → têm só `conteudo` (texto).
       Reconstrói o dict no formato esperado pelo BlocoRenderer.
    """
    # Mapeia tipos novos da Canção Nova pra tipos que o BlocoRenderer conhece
    TIPO_MAP = {
        "leitura_1": "primeira_leitura",
        "leitura_2": "segunda_leitura",
        "salmo": "leitura",  # LeituraCard renderiza igual
        "aclamacao": "leitura",
        "evangelho": "evangelho",
    }

    blocos: list[dict] = []
    for b in missa_db.blocos:
        if b.conteudo_estruturado:
            # Formato antigo (Arquidiocese)
            blocos.append(b.conteudo_estruturado)
        elif b.conteudo:
            # Formato novo (liturgia diária — só texto)
            tipo_renderizavel = TIPO_MAP.get(b.tipo, b.tipo)
            blocos.append({
                "ordem": b.ordem,
                "tipo": tipo_renderizavel,
                "tipo_original": b.tipo,
                "titulo": b.titulo,
                "referencia": b.referencia,
                "conteudo": b.conteudo,
                "texto": b.conteudo,
            })

    return {
        "id": missa_db.id,
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
