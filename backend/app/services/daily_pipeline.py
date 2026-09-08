"""Job diário: baixar PDF → parsear → persistir missa estruturada no BD."""
from __future__ import annotations

import logging
import os
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
    """Missas futuras sem evidência Gauntlet ou com versão antiga.

    São as missas montadas por uma versão ANTIGA das regras — candidatas a
    reprocesso automático. Só entram as que estão no ar (concluido): não mexe
    em pendente_revisao (já sob revisão humana)."""
    from app.services.persist_missa import conferencia_publicavel

    alvo = pipeline_version()
    candidatas = (
        db.query(MissaModel)
        .filter(MissaModel.data >= hoje)
        # Pendente é fila humana; só a migração explícita por PDF arquivado pode
        # reprocessá-la. A seleção automática não deve clobberar uma revisão.
        .filter(MissaModel.status_processamento == "concluido")
        .order_by(MissaModel.data.asc())
        .all()
    )
    return [
        m for m in candidatas
        if not conferencia_publicavel(m.revisao_json) or (m.pipeline_version or "") != alvo
    ]


def reter_montagens_sem_gauntlet(db) -> list[str]:
    """Retira da exposição qualquer edição concluída sem prova Gauntlet completa."""
    from app.services.persist_missa import conferencia_publicavel

    retidas: list[str] = []
    for missa in db.query(MissaModel).filter(MissaModel.status_processamento == "concluido").all():
        if conferencia_publicavel(missa.revisao_json):
            continue
        missa.status_processamento = "pendente_revisao"
        db.add(missa)
        retidas.append(missa.data.isoformat())
    if retidas:
        db.commit()
        logger.warning("Gauntlet: %d montagem(ns) legada(s) retida(s): %s", len(retidas), ", ".join(retidas))
    return retidas


def auto_atualizar_montagens(db, hoje: Optional[date] = None) -> dict:
    """Varre missas futuras montadas por versão antiga e reprocessa com segurança.

    Só reprocessa quem tem PDF arquivado (CACHE_DIR/archive/<data>.pdf). Cada
    reprocesso é não-regressivo: se cair em pendente_revisao, restaura o backup
    e mantém a montagem boa. Idempotente: após atualizar, a missa passa a ter a
    versão atual e não é mais selecionada."""
    from app.services.publicacao_convergente import montar_e_publicar
    from app.pipeline.extract import extrair_texto_estruturado
    from app.pipeline.clean import limpar

    # SEGURANÇA: a auto-atualização roda no event loop do scheduler e o fluxo
    # convergente é pesado (LLM de visão, minutos) — se rodar em rajada, BLOQUEIA
    # o worker (→ 502). Fica DESLIGADA por padrão no processo do serviço; rode-a
    # como processo separado (scripts/reprocessar_convergente.py) ou ligue com
    # AUTO_ATUALIZAR_MISSAS=1. LIMITE por tick evita tempestade.
    if os.getenv("AUTO_ATUALIZAR_MISSAS", "0").strip().lower() not in ("1", "true", "yes", "on"):
        return {"selecionadas": 0, "atualizadas": 0, "desligada": True}
    limite = int(os.getenv("AUTO_ATUALIZAR_LIMITE", "1"))

    hoje = hoje or date.today()
    alvos = selecionar_para_reprocesso(db, hoje)[:limite]
    resultados = []
    for m in alvos:
        pdf_path = CACHE_DIR / "archive" / f"{m.data.isoformat()}.pdf"
        if not pdf_path.exists():
            logger.info("auto-atualiza %s: sem PDF arquivado — pulando", m.data)
            resultados.append({"data": m.data.isoformat(), "resultado": "sem_pdf"})
            continue
        try:
            pdf_bytes = pdf_path.read_bytes()
            texto = limpar(extrair_texto_estruturado(pdf_path))
        except OSError as e:
            logger.warning("auto-atualiza %s: erro lendo PDF (%s)", m.data, e)
            resultados.append({"data": m.data.isoformat(), "resultado": "sem_pdf"})
            continue
        # Fluxo NOVO (conferência convergente): só montagem aprovada substitui;
        # reprovada/erro-de-montagem NÃO clobbera a boa existente (guarda item 0b).
        resultados.append(montar_e_publicar(db, m.data.isoformat(), pdf_bytes, texto))
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

    # A retenção não depende de rede ou do PDF de hoje. Ela precisa ocorrer até
    # quando o download falha, para que legado sem prova nunca continue público.
    db_retenção = SessionLocal()
    try:
        reter_montagens_sem_gauntlet(db_retenção)
    finally:
        db_retenção.close()

    try:
        conteudo = obter_pdf()
    except Exception as e:
        logger.exception("Falha no download do PDF")
        return {"status": "erro_download", "motivo": str(e)}

    h = hash_pdf(conteudo)
    # O PDF arquivado é a referência auditável do Gauntlet. Sem conseguir
    # preservá-lo, não existe fonte contra a qual a montagem possa ser conferida
    # ou reprocessada, portanto a publicação é bloqueada antes de tocar no BD.
    data_publicacao = date.today().isoformat()
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        pdf_path = CACHE_DIR / f"{h}.pdf"
        if not pdf_path.exists():
            pdf_path.write_bytes(conteudo)
        archive_dir = CACHE_DIR / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / f"{data_publicacao}.pdf"
        archive_path.write_bytes(conteudo)
    except (OSError, PermissionError) as e:
        logger.error("PDF não pôde ser arquivado em %s (%s) — publicação bloqueada", CACHE_DIR, e)
        return {"status": "erro_arquivamento", "motivo": str(e), "hash": h}

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

        # Gauntlet Loop: a montagem só pode seguir para publicação depois de uma
        # conferência independente contra este mesmo PDF.  ``processar_pdf``
        # continua disponível para testes determinísticos do parser, mas não é
        # uma rota de publicação de produção.
        from app.pipeline.extract import extrair_texto_estruturado
        from app.pipeline.clean import limpar
        from app.services.publicacao_convergente import montar_e_publicar

        texto_limpo = limpar(extrair_texto_estruturado(pdf_path))
        resultado = montar_e_publicar(db, data_publicacao, conteudo, texto_limpo)
        if resultado.get("resultado") != "publicada":
            return {
                "status": resultado.get("resultado", "pendente_revisao"),
                "data": resultado.get("data"),
                "hash": h,
                "conferencia": resultado,
            }
        missa_db = db.query(MissaModel).filter(MissaModel.data == resultado["data"]).first()
        if missa_db is None:
            raise RuntimeError("conferência aprovada sem missa persistida")
        logger.info(
            "Missa persistida id=%s data=%s blocos=%d",
            missa_db.id, missa_db.data, len(missa_db.blocos),
        )
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
