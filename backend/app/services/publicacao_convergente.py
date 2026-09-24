"""Passo 7 — publicação sob conferência convergente.

Só montagem APROVADA na conferência (passo 6) persiste/substitui. Reprovada NÃO
substitui uma montagem boa existente (concluida, sem fallback) — vai a e-mail. Se
não houver montagem boa, persiste como `pendente_revisao` para revisão humana.

Grava em `revisao_json.conferencia`: conferida, iteracoes, custo_usd, divergências
restantes. `pipeline_version` é gravada pelo próprio `persistir_missa`.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from datetime import date as _date, datetime, timezone

from sqlalchemy.orm import Session

from app.models.missa import Missa as MissaModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cache de resultado NÃO-convergido (opção B — corta o custo de retries).
#
# Quando uma tentativa com o MESMO PDF (sha256) e a MESMA configuração de
# modelos NÃO convergiu, refazer é desperdício garantido (~US$ 2+/retry, dia
# 23/09 queimou US$ 12 em 5 tentativas repetidas). Gravamos o veredito e, em
# retries subsequentes idênticos, devolvemos o resultado guardado SEM chamar o
# LLM de novo. O cache NÃO vale para execução nova (config diferente = chave
# diferente) nem bloqueia resposta humana: é só a repetição idêntica que corta.
# ---------------------------------------------------------------------------

def _fingerprint_modelos() -> str:
    """Chave de config: qualquer mudança de modelo/provedor/versão invalida o cache."""
    from app.core.pipeline_version import pipeline_version
    pedacos = [os.getenv(k, "") for k in (
        "LLM_PROVIDER", "ANTHROPIC_MODEL_MM", "MODELO_MAPA", "MODELO_CONFERENTE",
        "MONTAGEM_PYTHON_PRIMEIRO", "MONTAGEM_SEM_TEXTO_AUXILIAR",
    )]
    pedacos.append(f"pipeline_version={pipeline_version()}")
    return hashlib.sha256("|".join(pedacos).encode()).hexdigest()[:16]


def _caminho_cache_naoconv(data_iso: str, pdf_hash: str, celeb_hash: str) -> Path:
    from app.pipeline.download import CACHE_DIR
    return Path(CACHE_DIR) / "cache_naoconv" / f"{data_iso}-{pdf_hash[:10]}-{celeb_hash[:10]}.json"


def _ler_cache_naoconv(data_iso: str, pdf_hash: str, celeb_hash: str) -> dict | None:
    """Retorna o veredito anterior não-convergido se PDFs e config forem idênticos.

    Só reutiliza por até CACHE_NAOCONV_HORAS (default 6h) — tempo típico dos
    retries automáticos. Depois disso, executa de novo (não trava a produção).
    """
    try:
        caminho = _caminho_cache_naoconv(data_iso, pdf_hash, celeb_hash)
        if not caminho.exists():
            return None
        dados = json.loads(caminho.read_text())
        if dados.get("pdf_sha") != pdf_hash or dados.get("celeb_sha") != celeb_hash:
            return None
        if dados.get("fp") != _fingerprint_modelos():
            logger.info("cache não-conv %s ignorado: config de modelos mudou", data_iso)
            return None
        horas = float(os.getenv("CACHE_NAOCONV_HORAS", "6"))
        criado = datetime.fromisoformat(dados["criado_em"])
        if (datetime.now(timezone.utc) - criado).total_seconds() > horas * 3600:
            logger.info("cache não-conv %s expirado (%s)", data_iso, dados["criado_em"])
            return None
        return dados
    except Exception as e:  # noqa: BLE001
        logger.warning("leitura do cache não-conv %s falhou (%s) — roda de novo", data_iso, str(e)[:120])
        return None


def _gravar_cache_naoconv(data_iso: str, pdf_hash: str, celeb_hash: str, meta: dict) -> None:
    try:
        caminho = _caminho_cache_naoconv(data_iso, pdf_hash, celeb_hash)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        # Escrita atômica: grava em temp e renomeia — evita que um worker leia
        # JSON truncado escrevendo concorrente (2 workers uvicorn).
        tmp = caminho.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({
            "data": data_iso,
            "pdf_sha": pdf_hash,
            "celeb_sha": celeb_hash,
            "fp": _fingerprint_modelos(),
            "conferida": meta["conferida"],
            "iteracoes": meta["iteracoes"],
            "divergencias_restantes": meta["divergencias_restantes"],
            "criado_em": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False))
        os.replace(tmp, caminho)
    except Exception as e:  # noqa: BLE001
        logger.warning("gravação do cache não-conv %s falhou (%s)", data_iso, str(e)[:120])


def _custo_no_intervalo(db: Session, inicio: datetime) -> float:
    """Soma o custo_llm registrado desde `inicio` (custo real do fluxo desta missa)."""
    try:
        from app.models.custo_llm import CustoLLM
        rows = db.query(CustoLLM).filter(CustoLLM.data_criacao >= inicio).all()
        return round(sum(float(r.custo_usd or 0.0) for r in rows), 4)
    except Exception:
        return 0.0


def montar_e_publicar(db: Session, data_iso: str, pdf_bytes: bytes,
                      texto_limpo: str, *, pdf_celebrante_bytes: bytes | None = None,
                      fonte_celular_url: str | None = None,
                      fonte_celebrante_url: str | None = None,
                      fonte_celular_tipo: str | None = None,
                      fonte_celebrante_tipo: str | None = None) -> dict:
    """Roda o fluxo convergente e publica conforme a conferência.

    Retorna {data, resultado, conferida, iteracoes, custo_usd, divergencias}.
    resultado ∈ publicada | pendente_revisao | reprovada_mantida | erro_montagem.
    """
    from app.pipeline.montagem_convergente import montar_com_conferencia
    from app.pipeline.download import CACHE_DIR, hash_pdf
    from app.services.persist_missa import conferencia_publicavel, persistir_missa

    inicio = datetime.now(timezone.utc)
    data = _date.fromisoformat(data_iso)
    existente = db.query(MissaModel).filter(MissaModel.data == data).first()
    boa_existe = bool(existente and conferencia_publicavel(existente.revisao_json))

    # Retém legado antes de qualquer retorno por arquivo ausente/inválido.
    if existente and existente.status_processamento == "concluido" and not boa_existe:
        existente.status_processamento = "pendente_revisao"
        db.add(existente)
        db.commit()
        db.refresh(existente)

    pdf_arquivado = Path(CACHE_DIR) / "archive" / f"{data_iso}.pdf"
    if not pdf_arquivado.exists() or hash_pdf(pdf_arquivado.read_bytes()) != hash_pdf(pdf_bytes):
        logger.error("montagem bloqueada para %s: PDF oficial não está arquivado e íntegro", data_iso)
        return {"data": data_iso, "resultado": "bloqueado_sem_pdf_arquivado", "conferida": False,
                "iteracoes": 0, "custo_usd": 0.0}
    # O contrato exige duas fontes distintas e classificadas pela página oficial.
    # Não caímos para Assembleia, PDF genérico ou uma segunda chamada do mesmo PDF.
    pdf_celebrante_arquivado = Path(CACHE_DIR) / "archive" / f"{data_iso}-celebrante.pdf"
    if (
        not pdf_celebrante_bytes
        or not fonte_celular_url
        or not fonte_celebrante_url
        or fonte_celular_tipo != "celular"
        or fonte_celebrante_tipo != "celebrante"
        or not pdf_celebrante_arquivado.exists()
        or hash_pdf(pdf_celebrante_arquivado.read_bytes()) != hash_pdf(pdf_celebrante_bytes)
    ):
        logger.error("montagem bloqueada para %s: fontes Celular/Celebrante incompletas ou não arquivadas", data_iso)
        return {"data": data_iso, "resultado": "bloqueado_sem_fontes_oficiais", "conferida": False,
                "iteracoes": 0, "custo_usd": 0.0}
    # FREIOS DE GASTO — nenhum processo automático gasta ilimitado. Consulta antes de
    # qualquer chamada LLM: disjuntor de crédito (402), orçamento diário, teto/missa.
    from app.services import freios_gasto
    pode, motivo = freios_gasto.pode_montar(data_iso)
    if not pode:
        logger.warning("montagem BLOQUEADA por freio (%s) para %s", motivo, data_iso)
        # orçamento estourado dispara e-mail (com cooldown); demais motivos já foram
        # sinalizados no seu próprio canal (emergência/alerta).
        if "orçamento" in motivo:
            from app.services import monitor_llm
            monitor_llm.alerta_orcamento_diario(freios_gasto.gasto_do_dia(), freios_gasto.teto_diario())
        if not boa_existe and existente is not None:
            existente.status_processamento = "pendente_revisao"
            db.add(existente); db.commit()
        return {"data": data_iso, "resultado": "bloqueado_por_freio", "conferida": False,
                "iteracoes": 0, "custo_usd": 0.0, "motivo": motivo}
    # Cache de não-convergência (opção B): se esta mesma missa (mesmos PDFs e
    # mesma config) já NÃO convergiu há pouco, devolver o veredito SEM gastar LLM.
    # Rodado ANTES de registrar_tentativa: retry gratuito não consome o teto diário
    # de tentativas (só execução real paga consome).
    from app.pipeline.download import hash_pdf
    pdf_hash = hash_pdf(pdf_bytes)
    celeb_hash = hash_pdf(pdf_celebrante_bytes)
    cache_naoconv = _ler_cache_naoconv(data_iso, pdf_hash, celeb_hash)
    if cache_naoconv:
        # Replica o veredito real: se há montagem boa no ar, o resultado foi
        # reprovada_mantida; senão, pendente_revisao. Sem chamadas LLM.
        resultado_cache = "reprovada_mantida" if boa_existe else "pendente_revisao"
        logger.warning("REUTILIZADO cache não-convergido para %s (%d iter, %d divs) — sem chamada LLM",
                       data_iso, cache_naoconv["iteracoes"], len(cache_naoconv["divergencias_restantes"]))
        return {
            "data": data_iso, "resultado": resultado_cache,
            "conferida": False, "iteracoes": cache_naoconv["iteracoes"],
            "divergencias_restantes": cache_naoconv["divergencias_restantes"],
            "custo_usd": 0.0, "do_cache": True,
        }

    freios_gasto.registrar_tentativa(data_iso)

    # Passo 4 pode levantar (multimodal falhou) — NÃO cai para texto: agenda retry/alerta.
    try:
        missa_pyd, meta = montar_com_conferencia(
            pdf_bytes, texto_limpo, pdf_celebrante=pdf_celebrante_bytes, data_hint=data_iso
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("montagem multimodal falhou para %s — retry/alerta, NÃO publica", data_iso)
        # Emergência: falha por CRÉDITO/QUOTA → e-mail NA HORA + missa retida
        # (nunca publica degradada por falta de crédito; o retry reprocessa com saldo).
        from app.services import monitor_llm
        if monitor_llm.eh_erro_credito(e):
            provedor = "openrouter" if "openrouter" in str(e).lower() else "anthropic"
            monitor_llm.alerta_emergencia_credito(provedor, "montagem", data_iso, str(e))
            # Disjuntor: trava novas montagens até liberar_credito (sucesso pago ou manual).
            freios_gasto.bloquear_credito(f"402 {provedor} em {data_iso}: {str(e)[:120]}")
            resultado = "sem_credito"
        else:
            _alerta(data_iso, f"Montagem multimodal falhou: {str(e)[:200]}. Retry agendado.")
            resultado = "erro_montagem"
        # Se não há montagem boa existente, garante pendente_revisao para revisão humana.
        if not boa_existe and existente is not None:
            existente.status_processamento = "pendente_revisao"
            db.add(existente); db.commit()
        return {"data": data_iso, "resultado": resultado, "conferida": False,
                "iteracoes": 0, "custo_usd": _custo_no_intervalo(db, inicio), "motivo": str(e)[:200]}

    # Sucesso de uma montagem paga prova que há crédito → libera o disjuntor.
    freios_gasto.liberar_credito()

    custo = _custo_no_intervalo(db, inicio)
    conf = {"conferida": meta["conferida"], "iteracoes": meta["iteracoes"],
            "custo_usd": custo, "divergencias_restantes": meta["divergencias_restantes"],
            "contrato": meta.get("contrato", {}),
            "fontes": {
                "principal": {"tipo": "celular", "url": fonte_celular_url, "sha256": hash_pdf(pdf_bytes)},
                "secundaria": {"tipo": "celebrante", "url": fonte_celebrante_url,
                                "sha256": hash_pdf(pdf_celebrante_bytes)},
                "assembleia_foi_usada": False,
            }}

    if meta["conferida"]:
        # A evidência entra na mesma persistência que torna a missa visível. Assim
        # não há janela em que blocos novos fiquem ``concluido`` sem o veredito
        # independente anexado (nem notificação antecipada ao fiel).
        m = persistir_missa(db, missa_pyd, pdf_hash=hash_pdf(pdf_bytes),
                            fonte_url=fonte_celular_url, pdf_bytes=None,
                            revisao_json={"conferencia": conf})
        if m.status_processamento != "concluido":
            raise RuntimeError("conferência aprovada não satisfez o gate de persistência")
        logger.info("PUBLICADA %s (conferida, %d iter, US$ %.4f)", data_iso, meta["iteracoes"], custo)
        return {"data": data_iso, "resultado": "publicada", **conf}

    # Reprovada
    if boa_existe:
        _alerta(data_iso, f"Montagem reprovada na conferência ({meta['iteracoes']} iter). "
                          f"MANTIDA a montagem boa existente. Divergências: {meta['divergencias_restantes']}")
        logger.warning("REPROVADA %s — mantida a montagem boa existente", data_iso)
        _gravar_cache_naoconv(data_iso, pdf_hash, celeb_hash, meta)
        return {"data": data_iso, "resultado": "reprovada_mantida", **conf}

    # Sem montagem boa: persiste como pendente_revisao para revisão humana.
    m = persistir_missa(db, missa_pyd, pdf_hash=hash_pdf(pdf_bytes),
                        fonte_url=fonte_celular_url, pdf_bytes=None,
                        revisao_json={"conferencia": conf})
    if m.status_processamento != "pendente_revisao":
        raise RuntimeError("montagem reprovada não foi retida pelo gate de persistência")
    _alerta(data_iso, f"Montagem NÃO convergiu ({meta['iteracoes']} iter) e não havia montagem boa. "
                      f"pendente_revisao. Divergências: {meta['divergencias_restantes']}")
    logger.warning("PENDENTE_REVISAO %s (não convergiu)", data_iso)
    _gravar_cache_naoconv(data_iso, pdf_hash, celeb_hash, meta)
    return {"data": data_iso, "resultado": "pendente_revisao", **conf}


def _alerta(data_iso: str, msg: str) -> None:
    try:
        from app.services.verificador_lexical import enviar_alerta_lexical
        enviar_alerta_lexical(data_iso, [{"palavra": msg, "bloco": "conferência", "campo": "-", "contexto": ""}])
    except Exception:
        logger.warning("alerta conferência %s: %s", data_iso, msg)
