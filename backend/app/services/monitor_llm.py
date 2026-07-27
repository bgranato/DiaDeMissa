"""Monitoramento de consumo e crédito de LLM (digest semanal + alertas).

Motivado pelo bloqueio real por crédito zerado (22/07). Reusa custo_llm,
email_sender e o scheduler. NÃO usamos Auto-Reload (decisão de controle de
gastos) — por isso os alertas de limiar/pico e o retry-quando-houver-saldo.

Config via .env (tudo os.getenv, sem pydantic p/ não mexer no Settings):
  MONITOR_EMAILS             destinos dos alertas, lista separada por vírgula
                             (default: MONITOR_EMAIL; senão admins do banco)
  MONITOR_EMAIL              destino único (compat; use MONITOR_EMAILS p/ vários)
  MONITOR_SALDO_LIMIAR_USD   limiar de saldo baixo (default 5)
  MONITOR_PICO_FATOR         fator de pico de gasto 7d vs média (default 2.0)
  MONITOR_DIGEST             liga/desliga digest semanal (default 1)
  MONITOR_ALERTA_LIMIAR      liga/desliga alerta diário (default 1)
  MONITOR_ALERTA_EMERGENCIA  liga/desliga alerta de emergência (default 1)
  OPENROUTER_API_KEY         p/ saldo OpenRouter (GET /api/v1/credits)
  ANTHROPIC_ADMIN_KEY        p/ custo Anthropic (Admin API); senão "n/d — console"
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

LINKS_RECARGA = {
    "anthropic": "https://console.anthropic.com/settings/billing",
    "openrouter": "https://openrouter.ai/credits",
}
_INSTRUCAO = "Recarregue e o retry do fluxo convergente reprocessa a missa sozinho."


# ---------------------------------------------------------------- config helpers
def _f(env: str, default: float) -> float:
    try:
        return float(os.getenv(env, str(default)))
    except (TypeError, ValueError):
        return default


def _on(env: str, default: str = "1") -> bool:
    return os.getenv(env, default).strip().lower() in ("1", "true", "yes", "on")


def _agora() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------- cooldown / dedupe de alertas
# Anti-loop ESTRUTURAL: cada chave de alerta só reenvia após uma janela mínima.
# Persistido em arquivo JSON (sobrevive a restart e é compartilhado pelos 2 workers,
# então o segundo worker do scheduler não reenvia). Sem isso, um alerta cuja condição
# persiste (pico, saldo baixo) reenviaria a cada execução do job, e a emergência 402
# reenviaria a cada retry.
def _cooldown_path() -> Path:
    p = os.getenv("MONITOR_COOLDOWN_FILE", "").strip()
    if p:
        return Path(p)
    return Path(__file__).resolve().parents[2] / "data" / "monitor_cooldown.json"


def _cooldown_load() -> dict:
    try:
        return json.loads(_cooldown_path().read_text("utf-8"))
    except Exception:
        return {}


def _cooldown_save(d: dict) -> None:
    try:
        fp = _cooldown_path()
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(json.dumps(d), "utf-8")
    except Exception:
        logger.exception("monitor: falha ao salvar cooldown")


def _pode_enviar(chave: str, janela_seg: float) -> bool:
    """True se `chave` não foi enviada dentro de `janela_seg`. Se True, já registra o
    envio (marca agora) para o próximo teste respeitar a janela."""
    d = _cooldown_load()
    agora = _agora()
    ult = d.get(chave)
    if ult:
        try:
            quando = datetime.fromisoformat(ult)
            if (agora - quando).total_seconds() < janela_seg:
                return False
        except Exception:
            pass
    d[chave] = agora.isoformat()
    _cooldown_save(d)
    return True


_JANELA_24H = 24 * 3600
_JANELA_1H = 3600
_JANELA_SEMANA = 6 * 24 * 3600  # 6d: garante ≤1 por semana sem barrar o job semanal


def _destinatarios() -> list[str]:
    # MONITOR_EMAILS (plural, lista separada por vírgula) tem prioridade; MONITOR_EMAIL
    # (singular) mantido por compatibilidade. Dedup preservando ordem.
    alvo = (os.getenv("MONITOR_EMAILS", "") or os.getenv("MONITOR_EMAIL", "")).strip()
    if alvo:
        vistos, out = set(), []
        for e in alvo.split(","):
            e = e.strip()
            if e and e.lower() not in vistos:
                vistos.add(e.lower()); out.append(e)
        return out
    try:
        from app.core.database import SessionLocal
        from app.models.usuario import Usuario
        db = SessionLocal()
        try:
            return [a.email for a in db.query(Usuario).filter(Usuario.is_admin == True).all() if a.email]  # noqa: E712
        finally:
            db.close()
    except Exception:
        logger.exception("monitor: falha ao buscar admins")
        return []


def _enviar(assunto: str, html: str) -> bool:
    dests = _destinatarios()
    if not dests:
        logger.warning("monitor: sem destinatário para '%s'", assunto)
        return False
    from app.services.email_sender import enviar_email
    ok = True
    for d in dests:
        ok = enviar_email(d, assunto, html) and ok
    return ok


# ---------------------------------------------------------------- custo (custo_llm)
def gasto_por_etapa(inicio: datetime, fim: datetime | None = None) -> dict:
    """Soma custo_usd por contexto (etapa) no intervalo. Retorna {etapa: usd}."""
    from app.core.database import SessionLocal
    from app.models.custo_llm import CustoLLM
    fim = fim or datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        rows = db.query(CustoLLM).filter(
            CustoLLM.data_criacao >= inicio, CustoLLM.data_criacao < fim,
            CustoLLM.contexto != "erro_credito",
        ).all()
        por = {}
        for r in rows:
            et = _rotulo_etapa(r.contexto)
            por[et] = por.get(et, 0.0) + float(r.custo_usd or 0.0)
        return por
    finally:
        db.close()


def _rotulo_etapa(contexto: str | None) -> str:
    c = (contexto or "").lower()
    if c.startswith("conv:mapa"):
        return "mapa visual"
    if c.startswith("conv:montagem"):
        return "montagem"
    if c.startswith("conv:conferente"):
        return "conferente"
    if c == "gate":
        return "gate"
    return "outros"


def _total(d: dict) -> float:
    return round(sum(d.values()), 4)


# ---------------------------------------------------------------- saldos provedores
def saldo_openrouter() -> dict:
    """{provedor, saldo_usd|None, detalhe}. GET /api/v1/credits."""
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        return {"provedor": "openrouter", "saldo_usd": None, "detalhe": "sem OPENROUTER_API_KEY"}
    try:
        import httpx
        r = httpx.get("https://openrouter.ai/api/v1/credits",
                      headers={"Authorization": f"Bearer {key}"}, timeout=15)
        r.raise_for_status()
        d = (r.json() or {}).get("data") or {}
        saldo = round(float(d.get("total_credits", 0)) - float(d.get("total_usage", 0)), 4)
        return {"provedor": "openrouter", "saldo_usd": saldo, "detalhe": "ok"}
    except Exception as e:  # noqa: BLE001
        return {"provedor": "openrouter", "saldo_usd": None, "detalhe": f"erro: {str(e)[:80]}"}


def saldo_anthropic() -> dict:
    """Anthropic não expõe SALDO; a Admin API dá custo (requer sk-ant-admin...).
    Sem chave admin → n/d (conferir no console)."""
    adm = os.getenv("ANTHROPIC_ADMIN_KEY", "").strip()
    if not adm:
        return {"provedor": "anthropic", "saldo_usd": None,
                "detalhe": "n/d — conferir no console (sem ANTHROPIC_ADMIN_KEY)"}
    try:
        import httpx
        ini = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00Z")
        r = httpx.get("https://api.anthropic.com/v1/organizations/cost_report",
                      headers={"x-api-key": adm, "anthropic-version": "2023-06-01"},
                      params={"starting_at": ini}, timeout=15)
        r.raise_for_status()
        # custo (não saldo) — informativo
        return {"provedor": "anthropic", "saldo_usd": None,
                "detalhe": f"custo 7d via Admin API: {r.json()}"[:200]}
    except Exception as e:  # noqa: BLE001
        return {"provedor": "anthropic", "saldo_usd": None,
                "detalhe": f"n/d — conferir no console (Admin API: {str(e)[:60]})"}


def _bloco_saldos_html() -> str:
    linhas = []
    for s in (saldo_openrouter(), saldo_anthropic()):
        saldo = f"US$ {s['saldo_usd']:.2f}" if s["saldo_usd"] is not None else "n/d"
        link = LINKS_RECARGA.get(s["provedor"], "")
        linhas.append(f"<li><b>{s['provedor']}</b>: saldo {saldo} — {s['detalhe']} "
                      f"(<a href='{link}'>recarregar</a>)</li>")
    # Auto-Reload: não usamos por decisão de controle de gastos
    linhas.append("<li><b>Auto-Reload</b>: DESLIGADO por decisão de controle de gastos — "
                  "conferência/recarga é manual.</li>")
    return "<ul>" + "".join(linhas) + "</ul>"


def _links_recarga_html() -> str:
    itens = "".join(f"<li><a href='{u}'>{p.capitalize()}: {u}</a></li>"
                    for p, u in LINKS_RECARGA.items())
    return f"<p><b>Recarregar:</b></p><ul>{itens}</ul><p><i>{_INSTRUCAO}</i></p>"


# ---------------------------------------------------------------- DIGEST semanal
def montar_digest() -> tuple[str, str]:
    """Retorna (assunto, html) do digest da última semana. Não envia."""
    agora = _agora()
    ini_semana = agora - timedelta(days=7)
    etapas = gasto_por_etapa(ini_semana, agora)
    total = _total(etapas)
    projecao_mensal = round(total / 7 * 30, 2)
    # média das 4 semanas anteriores (semanas -2..-5)
    medias = []
    for k in range(2, 6):
        a = agora - timedelta(days=7 * k)
        b = agora - timedelta(days=7 * (k - 1))
        medias.append(_total(gasto_por_etapa(a, b)))
    media4 = round(sum(medias) / len(medias), 4) if medias else 0.0
    delta = ("+" if total >= media4 else "") + (f"{(total-media4):.2f}")

    linhas_etapa = "".join(
        f"<tr><td>{et}</td><td style='text-align:right'>US$ {v:.2f}</td></tr>"
        for et, v in sorted(etapas.items(), key=lambda x: -x[1])
    ) or "<tr><td colspan=2>sem gastos na semana</td></tr>"

    html = (
        f"<h2>Digest semanal de consumo LLM — Dia de Missa</h2>"
        f"<p>Período: últimos 7 dias (até {agora.strftime('%d/%m/%Y')} UTC).</p>"
        f"<h3>Gasto por etapa</h3><table border=1 cellpadding=6 cellspacing=0>{linhas_etapa}"
        f"<tr><td><b>TOTAL</b></td><td style='text-align:right'><b>US$ {total:.2f}</b></td></tr></table>"
        f"<p><b>Projeção mensal:</b> US$ {projecao_mensal:.2f} · "
        f"<b>Média das 4 semanas anteriores:</b> US$ {media4:.2f} "
        f"(<b>Δ US$ {delta}</b> vs. média).</p>"
        f"<h3>Saldo de créditos / Auto-Reload</h3>{_bloco_saldos_html()}"
        f"{_links_recarga_html()}"
    )
    return (f"[Dia de Missa] Digest LLM — US$ {total:.2f} na semana", html)


def enviar_digest_semanal() -> dict:
    if not _on("MONITOR_DIGEST"):
        return {"enviado": False, "motivo": "desligado (MONITOR_DIGEST)"}
    if not _pode_enviar("digest", _JANELA_SEMANA):
        return {"enviado": False, "motivo": "cooldown (já enviado nesta semana)"}
    assunto, html = montar_digest()
    return {"enviado": _enviar(assunto, html), "assunto": assunto}


# ---------------------------------------------------------------- ALERTA de limiar
def _erros_credito_recentes(horas: int = 24) -> int:
    from app.core.database import SessionLocal
    from app.models.custo_llm import CustoLLM
    desde = _agora() - timedelta(hours=horas)
    db = SessionLocal()
    try:
        return db.query(CustoLLM).filter(
            CustoLLM.contexto == "erro_credito", CustoLLM.data_criacao >= desde).count()
    finally:
        db.close()


def checar_limiares() -> dict:
    """Avalia os 3 gatilhos e envia e-mail se algum disparar. Retorna o diagnóstico."""
    agora = _agora()
    limiar = _f("MONITOR_SALDO_LIMIAR_USD", 5.0)
    fator = _f("MONITOR_PICO_FATOR", 2.0)
    # (chave_cooldown, texto). Cada gatilho tem sua própria janela de 24h — assim uma
    # condição que persiste (pico, saldo baixo) não reenvia a cada execução do job.
    candidatos = []

    # (a) saldo baixo
    saldos = [saldo_openrouter(), saldo_anthropic()]
    for s in saldos:
        if s["saldo_usd"] is not None and s["saldo_usd"] < limiar:
            candidatos.append((f"saldo:{s['provedor']}",
                               f"Saldo BAIXO em <b>{s['provedor']}</b>: US$ {s['saldo_usd']:.2f} "
                               f"(&lt; limiar US$ {limiar:.2f})."))

    # (b) pico: gasto 7d > fator × média histórica (semanas -2..-5)
    total7 = _total(gasto_por_etapa(agora - timedelta(days=7), agora))
    medias = [_total(gasto_por_etapa(agora - timedelta(days=7 * k), agora - timedelta(days=7 * (k - 1))))
              for k in range(2, 6)]
    media4 = sum(medias) / len(medias) if medias else 0.0
    if media4 > 0 and total7 > fator * media4:
        candidatos.append(("pico",
                           f"PICO de gasto: US$ {total7:.2f} nos últimos 7 dias &gt; "
                           f"{fator:.0f}× a média histórica (US$ {media4:.2f}). Possível loop/bug gastador."))

    # (c) erro de crédito/quota nas últimas 24h
    n_erros = _erros_credito_recentes(24)
    if n_erros:
        candidatos.append(("erro_credito_24h",
                           f"{n_erros} erro(s) de crédito/quota de LLM nas últimas 24h."))

    diag = {"limiar": limiar, "total7": total7, "media4": round(media4, 4),
            "erros_credito_24h": n_erros,
            "alertas": [t for _, t in candidatos], "enviado": False}
    if not _on("MONITOR_ALERTA_LIMIAR"):
        diag["motivo"] = "desligado (MONITOR_ALERTA_LIMIAR)"
        return diag

    # Dedupe: só inclui no e-mail os gatilhos fora do cooldown de 24h.
    frescos = [t for chave, t in candidatos if _pode_enviar(f"limiar:{chave}", _JANELA_24H)]
    diag["suprimidos"] = len(candidatos) - len(frescos)
    if frescos:
        html = ("<h2>⚠️ Alerta de crédito/consumo LLM — Dia de Missa</h2><ul>"
                + "".join(f"<li>{a}</li>" for a in frescos) + "</ul>" + _links_recarga_html())
        diag["enviado"] = _enviar("[Dia de Missa] ALERTA de crédito/consumo LLM", html)
    elif candidatos:
        diag["motivo"] = "cooldown (todos os gatilhos já alertados nas últimas 24h)"
    return diag


# ------------------------------------------------------------- ALERTA de emergência
def eh_erro_credito(exc: Exception | str) -> bool:
    """Detecta erro de crédito/quota (Anthropic 400 'credit balance', OpenRouter 402)."""
    m = (str(exc) or "").lower()
    return any(t in m for t in (
        "credit balance", "insufficient", "quota", "402", "billing",
        "payment required", "too low",
    ))


def registrar_erro_credito(provedor: str, etapa: str, data_missa: str) -> None:
    """Marca o erro em custo_llm (contexto='erro_credito') p/ o alerta diário (2c)."""
    try:
        from app.services.custo_llm_service import registrar_custo_llm
        registrar_custo_llm(f"{provedor}", 0, 0, 0.0, contexto="erro_credito", referencia=data_missa)
    except Exception:
        logger.exception("monitor: falha ao registrar erro_credito")


def alerta_emergencia_credito(provedor: str, etapa: str, data_missa: str, detalhe: str = "") -> bool:
    """E-mail NA HORA quando uma chamada LLM falha por crédito/quota."""
    # Sempre registra a ocorrência (alimenta o gatilho 2c do alerta diário)...
    registrar_erro_credito(provedor, etapa, data_missa)
    if not _on("MONITOR_ALERTA_EMERGENCIA"):
        return False
    # ...mas o E-MAIL é 1 por hora por (provedor, missa) — o 402 dispara a cada retry.
    if not _pode_enviar(f"402:{provedor}:{data_missa}", _JANELA_1H):
        logger.info("monitor: emergencia 402 em cooldown (%s/%s)", provedor, data_missa)
        return False
    html = (
        f"<h2>🚨 SEM CRÉDITO LLM — montagem retida</h2>"
        f"<p>Provedor: <b>{provedor}</b> · Etapa: <b>{etapa}</b> · Missa: <b>{data_missa}</b></p>"
        f"<p>A montagem NÃO foi publicada (fica <b>pendente_revisao</b>) — nunca publicamos "
        f"montagem degradada por falta de crédito.</p>"
        f"<p>Detalhe: {detalhe[:300]}</p>" + _links_recarga_html()
    )
    return _enviar(f"[Dia de Missa] 🚨 SEM CRÉDITO — missa {data_missa} retida", html)
