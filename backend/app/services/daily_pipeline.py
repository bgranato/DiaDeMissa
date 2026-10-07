"""Verificador diário das fontes oficiais: detecta edições novas → baixa → monta → persiste."""
from __future__ import annotations

import logging
import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Optional

from app.core.database import SessionLocal
from app.core.pipeline_version import pipeline_version
from app.models.missa import Missa as MissaModel
from app.pipeline.download import (
    CACHE_DIR,
    baixar_fontes_oficiais,
    datas_disponiveis,
    hash_pdf,
    obter_pagina_folhetos,
)
from app.services.persist_missa import conferencia_publicavel, persistir_missa

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
        pdf_celebrante_path = CACHE_DIR / "archive" / f"{m.data.isoformat()}-celebrante.pdf"
        if not pdf_celebrante_path.exists():
            logger.info("auto-atualiza %s: sem PDF Celebrante arquivado — pulando", m.data)
            resultados.append({"data": m.data.isoformat(), "resultado": "sem_pdf_celebrante"})
            continue
        fontes = ((m.revisao_json or {}).get("conferencia", {}).get("fontes", {}))
        fonte_celular = fontes.get("principal") or {}
        fonte_celebrante = fontes.get("secundaria") or {}
        url_celular = fonte_celular.get("url")
        url_celebrante = fonte_celebrante.get("url")
        if not url_celular or not url_celebrante:
            logger.info("auto-atualiza %s: sem evidência das fontes oficiais — pulando", m.data)
            resultados.append({"data": m.data.isoformat(), "resultado": "sem_evidencia_fontes"})
            continue
        resultados.append(montar_e_publicar(
            db, m.data.isoformat(), pdf_bytes, texto,
            pdf_celebrante_bytes=pdf_celebrante_path.read_bytes(),
            fonte_celular_url=url_celular,
            fonte_celebrante_url=url_celebrante,
            fonte_celular_tipo=fonte_celular.get("tipo"),
            fonte_celebrante_tipo=fonte_celebrante.get("tipo"),
        ))
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


def executar_pipeline_diario(forcar: bool = False, data_referencia: date | None = None) -> dict:
    """Verificador barato das fontes oficiais: detecta edições novas e monta só o que falta.

    Modo automático (``data_referencia`` omitido — cron e rotas): o verificador
    lê a página de folhetos UMA vez (1 GET), lista as edições completas
    (Celular + Celebrante) com data >= hoje e processa cada alvo:

    1. missa já ``concluido`` + Gauntlet completo → ``ja_publicada`` SEM baixar
       PDF e SEM chamada LLM — o ciclo com tudo publicado custa só o GET;
    2. demais → baixa PDFs (HTML reaproveitado, sem refetch) → idempotência por
       hash → monta via ``montar_e_publicar`` (convergência + Gauntlet).

    Datas passadas e edições incompletas ficam de fora do modo automático: não
    há mais ``FonteFolhetoIndisponivel`` em dia sem folheto. Falha de página por
    data não interrompe as demais.

    Modo explícito (``data_referencia``): processa SÓ essa data com o contrato
    antigo (download + idempotência por hash), inclusive no passado — rota
    ``processar-pdf`` e scripts. ``forcar=True`` pula a pulagem e o hash nos dois
    modos.

    Returns:
        dict com {status, motivo, hoje, resultados, auto_atualizacao?}. Quando há
        um único alvo, as chaves dele (missa_id, data, hash...) são espelhadas no
        topo para manter o contrato antigo.
    """
    hoje = date.today()
    verificador = data_referencia is None
    modo = "verificador" if verificador else "explícito"
    logger.info(
        "Iniciando pipeline diário [%s] (forcar=%s, referencia=%s)",
        modo, forcar, data_referencia,
    )

    # A retenção não depende de rede ou do PDF de hoje. Ela precisa ocorrer até
    # quando o download falha, para que legado sem prova nunca continue público.
    db_retenção = SessionLocal()
    try:
        reter_montagens_sem_gauntlet(db_retenção)
    finally:
        db_retenção.close()

    try:
        html = obter_pagina_folhetos()
    except Exception as e:
        logger.exception("Falha ao ler a página de folhetos da Arquidiocese")
        return {"status": "erro_download", "motivo": str(e), "hoje": hoje.isoformat(), "resultados": []}

    if verificador:
        alvos = [d for d in datas_disponiveis(html) if d >= hoje]
    else:
        alvos = [data_referencia]
    if not alvos:
        logger.info("Nenhuma edição nova nas fontes oficiais (hoje=%s) — sem download, sem LLM.", hoje)
        return {
            "status": "sem_novidade",
            "motivo": "nenhuma edição completa disponível na página oficial",
            "hoje": hoje.isoformat(),
            "resultados": [],
        }
    logger.info("Edições candidatas: %s", ", ".join(d.isoformat() for d in alvos))

    db = SessionLocal()
    try:
        resultados: list[dict] = []
        baixou = False
        for data_alvo in alvos:
            try:
                resultado = _processar_edicao(db, data_alvo, html, forcar=forcar, verificador=verificador)
            except Exception as e:
                logger.exception("Falha ao processar edição %s", data_alvo)
                db.rollback()
                resultado = {"status": "erro_parse", "motivo": str(e), "data": data_alvo.isoformat()}
            resultados.append(resultado)
            baixou = baixou or resultado["status"] in ("ok", "ignorado")

        # Mesmo sem folheto novo para esta data, varre missas futuras montadas por
        # versão antiga (a evolução do pipeline não pode deixar buracos). Só roda
        # se houve download nesta execução — o mesmo gatilho do código antigo.
        auto = auto_atualizar_montagens(db) if baixou else None
        resumo: dict = {
            "status": _status_geral(resultados),
            "motivo": _motivo_geral(resultados),
            "hoje": hoje.isoformat(),
            "resultados": resultados,
        }
        if auto is not None:
            resumo["auto_atualizacao"] = auto
        if len(resultados) == 1:
            resumo.update({k: v for k, v in resultados[0].items() if k not in resumo})
        logger.info("Pipeline diário [%s] concluído: status=%s", modo, resumo["status"])
        return resumo
    finally:
        db.close()


def _processar_edicao(db, data_alvo: date, html: str, *, forcar: bool, verificador: bool) -> dict:
    """Baixa, arquiva e monta uma edição. Uma falha aqui não zera as demais."""
    iso = data_alvo.isoformat()

    # PULO barato (só modo verificador): montagem concluída + Gauntlet completo
    # → sem download e sem LLM. É o "montou 1x, espera a próxima".
    if verificador and not forcar:
        publicada = (
            db.query(MissaModel)
            .filter(MissaModel.data == data_alvo)
            .filter(MissaModel.status_processamento == "concluido")
            .first()
        )
        if publicada is not None and conferencia_publicavel(publicada.revisao_json):
            logger.info("Missa %s já publicada (id=%s) — sem download nem remontagem", iso, publicada.id)
            return {
                "status": "ja_publicada",
                "motivo": "montagem concluída e conferida",
                "data": iso,
                "missa_id": publicada.id,
            }

    try:
        fonte_celular, conteudo, fonte_celebrante, conteudo_celebrante = baixar_fontes_oficiais(data_alvo, html=html)
    except Exception as e:
        logger.exception("Falha no download das fontes oficiais Celular/Celebrante (%s)", iso)
        return {"status": "erro_download", "motivo": str(e), "data": iso}

    h = hash_pdf(conteudo)
    # O PDF arquivado é a referência auditável do Gauntlet. Sem conseguir
    # preservá-lo, não existe fonte contra a qual a montagem possa ser conferida
    # ou reprocessada, portanto a publicação é bloqueada antes de tocar no BD.
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        pdf_path = CACHE_DIR / f"{h}.pdf"
        if not pdf_path.exists():
            pdf_path.write_bytes(conteudo)
        archive_dir = CACHE_DIR / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        (archive_dir / f"{iso}.pdf").write_bytes(conteudo)
        (archive_dir / f"{iso}-celebrante.pdf").write_bytes(conteudo_celebrante)
    except (OSError, PermissionError) as e:
        logger.error("PDF não pôde ser arquivado em %s (%s) — publicação bloqueada", CACHE_DIR, e)
        return {"status": "erro_arquivamento", "motivo": str(e), "data": iso, "hash": h}

    if not forcar:
        existente = db.query(MissaModel).filter(MissaModel.pdf_hash == h).first()
        if existente:
            logger.info("PDF não alterado (hash %s). Missa id=%s já no BD.", h[:8], existente.id)
            return {
                "status": "ignorado",
                "motivo": "hash inalterado",
                "data": iso,
                "missa_id": existente.id,
                "hash": h,
            }

    # Gauntlet Loop: a montagem só pode seguir para publicação depois de uma
    # conferência independente contra este mesmo PDF.  ``processar_pdf``
    # continua disponível para testes determinísticos do parser, mas não é
    # uma rota de publicação de produção.
    from app.pipeline.clean import limpar
    from app.pipeline.extract import extrair_texto_estruturado
    from app.services.publicacao_convergente import montar_e_publicar

    try:
        texto_limpo = limpar(extrair_texto_estruturado(pdf_path))
        resultado = montar_e_publicar(
            db, iso, conteudo, texto_limpo,
            pdf_celebrante_bytes=conteudo_celebrante,
            fonte_celular_url=fonte_celular.url,
            fonte_celebrante_url=fonte_celebrante.url,
            fonte_celular_tipo=fonte_celular.tipo,
            fonte_celebrante_tipo=fonte_celebrante.tipo,
        )
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
        return {
            "status": "ok",
            "motivo": "montada e conferida",
            "data": missa_db.data.isoformat(),
            "missa_id": missa_db.id,
            "hash": h,
            "blocos": len(missa_db.blocos),
        }
    except Exception as e:
        logger.exception("Falha no parsing/persistência (%s)", iso)
        db.rollback()
        return {"status": "erro_parse", "motivo": str(e), "data": iso, "hash": h}


def _status_geral(resultados: list[dict]) -> str:
    """Status único para o lote: erros → montagem concluída → demais → puro skip."""
    if not resultados:
        return "sem_novidade"
    for r in resultados:
        if str(r.get("status", "")).startswith("erro"):
            return r["status"]
    if any(r.get("status") == "ok" for r in resultados):
        return "ok"
    demais = [r.get("status") for r in resultados if r.get("status") != "ja_publicada"]
    if demais:
        return demais[0]
    return "ja_publicada"


def _motivo_geral(resultados: list[dict]) -> str:
    if not resultados:
        return "nenhuma edição nova"
    contagem: dict[str, int] = {}
    for r in resultados:
        contagem[r.get("status", "?")] = contagem.get(r.get("status", "?"), 0) + 1
    return f"{len(resultados)} edição(ões): " + ", ".join(f"{v}x {k}" for k, v in sorted(contagem.items()))
