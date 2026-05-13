"""APScheduler com job diário às 5h da manhã."""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.daily_pipeline import executar_pipeline_diario
from app.services.notif_nao_acompanhou import gerar_notificacoes_nao_acompanhada

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def iniciar_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    sched = BackgroundScheduler(timezone="America/Sao_Paulo")
    sched.add_job(
        executar_pipeline_diario,
        CronTrigger(hour=5, minute=0),
        id="download_folheto_diario",
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
    sched.start()
    logger.info(
        "Scheduler iniciado. Pipeline 5h, notif nao_acompanhou 22h. Próxima pipeline: %s",
        sched.get_job("download_folheto_diario").next_run_time,
    )
    _scheduler = sched
    return sched


def parar_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
