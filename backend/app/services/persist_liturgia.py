"""Persiste liturgia diária scraped do Canção Nova como Missa completa no BD.

Estratégia: combina Missal Padrão (Ordinário fixo da missa) + leituras do dia.
O resultado é uma missa estruturada com ~25 blocos, idêntica em diagramação ao
folheto da Arquidiocese RJ — com seções (Ritos Iniciais, Liturgia da Palavra,
Liturgia Eucarística, Ritos de Conclusão), posturas (de pé / sentado / ajoelhado)
e tipos de bloco renderizáveis pelo BlocoRenderer.

Idempotente: se já existe missa pra data, reusa o id e reconstrói os blocos.
"""
from __future__ import annotations

import logging
from datetime import date as date_type

from sqlalchemy.orm import Session

from app.models.missa import Missa, BlocoLiturgico
from app.services.missal_padrao import montar_missa_completa

logger = logging.getLogger(__name__)


def persistir_liturgia_diaria(db: Session, data_dict: dict) -> Missa:
    """Cria ou atualiza uma Missa a partir do dict retornado por buscar_liturgia().

    REGRA IMPORTANTE: não sobrescreve missas que já vieram do folheto Arquidiocese RJ
    (fonte arqrio.com.br) — esse folheto é muito mais rico (cantos próprios, antífonas,
    Oração Eucarística completa) que o template CNBB. Domingos e solenidades importantes
    têm folheto Arquidiocese; dias comuns caem no CNBB.
    """
    raise RuntimeError(
        "Liturgia CNBB/Missal sem PDF oficial não pode ser persistida: "
        "use o pipeline convergente PDF × montagem."
    )

    data_iso = data_dict["data"]
    data_obj = date_type.fromisoformat(data_iso)

    missa = db.query(Missa).filter(Missa.data == data_obj).first()

    # Proteção: se a missa atual vem do folheto Arquidiocese, não substitui pela CNBB.
    if missa and missa.fonte_pdf_url and "arqrio" in missa.fonte_pdf_url:
        logger.info(
            "Missa %s já tem folheto Arquidiocese (id=%s, %d blocos) — não substituindo pela CNBB.",
            data_obj, missa.id, len(missa.blocos),
        )
        return missa

    if missa is None:
        missa = Missa(
            data=data_obj,
            fonte_pdf_url=data_dict.get("fonte_url", "https://liturgia.cancaonova.com/pb/"),
        )
        db.add(missa)

    # Atualiza metadados
    missa.celebracao = data_dict.get("titulo")
    missa.tempo_liturgico = data_dict.get("tempo_liturgico")
    missa.descricao = f"Cor litúrgica: {data_dict['cor_liturgica']}" if data_dict.get("cor_liturgica") else None
    # Liturgia CNBB/Missal não tem o PDF oficial da Arquidiocese para conferir.
    # Portanto jamais pode ser publicada como se tivesse passado pelo Gauntlet.
    missa.status_processamento = "pendente_revisao"
    missa.revisao_json = {"conferencia": {
        "conferida": False,
        "divergencias_restantes": [],
        "motivo": "sem PDF oficial da Arquidiocese para conferência independente",
    }}

    # Palavra do dia = início do Evangelho
    if data_dict.get("evangelho", {}).get("texto"):
        texto_ev = data_dict["evangelho"]["texto"]
        primeira_frase = texto_ev.split(".")[0].strip()
        if len(primeira_frase) > 20:
            missa.palavra_do_dia = {
                "texto": primeira_frase[:300],
                "referencia": data_dict["evangelho"].get("referencia") or "",
            }

    # Remove blocos antigos (rebuild completo)
    if missa.id:
        db.query(BlocoLiturgico).filter(BlocoLiturgico.missa_id == missa.id).delete()
        db.flush()

    # Monta a missa completa (Missal Padrão + leituras do dia)
    blocos_estruturados = montar_missa_completa(
        leituras=data_dict,
        data=data_obj,
        tempo_liturgico=data_dict.get("tempo_liturgico"),
    )

    for b in blocos_estruturados:
        # `conteudo` simples: pega do bloco se for leitura/oração/canto com texto puro
        conteudo_texto = b.get("conteudo") if isinstance(b.get("conteudo"), str) else None

        bloco_db = BlocoLiturgico(
            missa=missa,
            ordem=b["ordem"],
            tipo=b["tipo"],
            titulo=b.get("titulo"),
            referencia=b.get("referencia"),
            conteudo=conteudo_texto,
            conteudo_estruturado=b,  # JSON completo para o BlocoRenderer
            visivel=True,
        )
        db.add(bloco_db)

    db.commit()
    db.refresh(missa)

    # Compare-and-commit: auditoria síncrona antes de "publicar".
    # Se houver achado CRÍTICO, marca pendente_revisao pra esconder do app
    # até revisão manual ou novo processamento.
    try:
        from app.services.auditor_missa import auditar_missa
        rel = auditar_missa(missa)
        if rel.tem_critica:
            missa.status_processamento = "pendente_revisao"
            db.add(missa)
            db.commit()
            db.refresh(missa)
            logger.warning(
                "Missa %s marcada pendente_revisao (%d achado(s) crítico(s)). Severidade=%s",
                data_obj,
                sum(1 for a in rel.achados if a.severidade == "CRÍTICA"),
                rel.severidade_max,
            )
        elif rel.achados:
            logger.info(
                "Missa %s publicada com %d achado(s) não-crítico(s) (%s)",
                data_obj, len(rel.achados), rel.severidade_max,
            )
    except Exception:
        logger.exception("Falha ao auditar missa %s (não bloqueante)", data_obj)

    return missa
