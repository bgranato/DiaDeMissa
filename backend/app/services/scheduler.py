"""APScheduler com job diário às 5h da manhã."""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.daily_pipeline import executar_pipeline_diario
from app.services.atualizacao_igrejas_job import atualizar_catalogo_igrejas
from app.services.notif_nao_acompanhou import gerar_notificacoes_nao_acompanhada
from app.services.auditor_missa import executar_auditoria
from app.services.alerta_folheto_faltando import alertar_folheto_faltando

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def iniciar_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    sched = BackgroundScheduler(timezone="America/Sao_Paulo")

    # Folheto Arquidiocese (PDF). Roda 5h da manhã.
    sched.add_job(
        executar_pipeline_diario,
        CronTrigger(hour=5, minute=0),
        id="download_folheto_diario",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    # Re-tentativa do Arquidiocese de hora em hora durante o dia.
    # Se o cron das 5h falhou (filesystem read-only, rede, etc.) OU se o folheto
    # foi publicado após esse horário, tentamos de novo a cada hora.
    # Idempotente: se hash não mudou (já temos), o pipeline retorna 'ignorado'.
    # Sobrescreve missa CNBB se Arquidiocese chega depois (proteção interna inverte:
    # CNBB nunca sobrescreve Arquidiocese, mas Arquidiocese sempre sobrescreve CNBB).
    sched.add_job(
        executar_pipeline_diario,
        CronTrigger(hour="6-22", minute=0),
        id="folheto_arqrio_retry_horario",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    # (Removido) Job CNBB/Canção Nova + Missal Padrão: fabricava o Ordinário dos
    # dias de semana. Regra "só folheto": as missas vêm EXCLUSIVAMENTE do folheto
    # da Arquidiocese (pipeline acima). Dias sem folheto ficam sem missa.
    # Auditoria automática — varre missas processadas, detecta problemas
    # (preces amassadas, blocos vazios, artefatos vazando) e marca pendente_revisao.
    # 5h15 dá tempo do pipeline + persistência terminarem.
    sched.add_job(
        executar_auditoria,
        CronTrigger(hour=5, minute=15),
        id="auditoria_missas",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    # Atualização semanal do catálogo de igrejas (Arquidiocese RJ) — segundas 4h.
    # Mantém endereços, telefones, horários sempre atualizados de forma incremental.
    sched.add_job(
        atualizar_catalogo_igrejas,
        CronTrigger(day_of_week="mon", hour=4, minute=0),
        id="atualizar_igrejas_semanal",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    # Notificação 'não acompanhou' — roda à noite, processa missa do dia anterior
    sched.add_job(
        gerar_notificacoes_nao_acompanhada,
        CronTrigger(hour=22, minute=0),
        id="notif_nao_acompanhou",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    # Vigia de folheto faltando — alerta admins por e-mail se o domingo iminente
    # ficar sem missa. Sábado 13h (aviso, com tempo de recuperar do mirror) +
    # domingo 8h (escalada). Se a missa for capturada no meio, o domingo não alerta.
    sched.add_job(
        alertar_folheto_faltando,
        CronTrigger(day_of_week="sat", hour=13, minute=0),
        id="alerta_folheto_sabado",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    sched.add_job(
        alertar_folheto_faltando,
        CronTrigger(day_of_week="sun", hour=8, minute=0),
        id="alerta_folheto_domingo",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    # Monitoramento de consumo/crédito de LLM.
    from app.services.monitor_llm import enviar_digest_semanal, checar_limiares
    # Digest semanal — segunda 08h (BRT, tz do scheduler).
    sched.add_job(
        enviar_digest_semanal,
        CronTrigger(day_of_week="mon", hour=8, minute=0),
        id="llm_digest_semanal", replace_existing=True, max_instances=1, coalesce=True,
    )
    # Alerta de limiar/pico/erro-de-crédito — diário 07h.
    sched.add_job(
        checar_limiares,
        CronTrigger(hour=7, minute=0),
        id="llm_alerta_limiar", replace_existing=True, max_instances=1, coalesce=True,
    )
    sched.start()
    logger.info(
        "Scheduler iniciado. Folheto Arquidiocese 5h (+retry horário), auditoria 5h15, notif 22h.",
    )
    _scheduler = sched
    return sched


def parar_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
