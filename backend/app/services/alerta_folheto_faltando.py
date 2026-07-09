"""Alerta admin: domingo sem folheto capturado (redundância / vigia).

A fonte do arqrio é uma URL rotativa que serve só o folheto vigente — se a
captura de uma semana falha (ou o folheto é publicado tarde), aquela edição
sai do ar e o domingo fica sem missa, silenciosamente (foi o caso de 31/05).

Este job roda no SÁBADO (aviso) e no DOMINGO de manhã (escalada): se o próximo
domingo (ou hoje, se domingo) não tem missa CONCLUÍDA no banco, envia e-mail aos
administradores para recuperarem o folheto manualmente (mirror de paróquia)
enquanto ainda está disponível.

Limitação conhecida (fase 1): cobre DOMINGOS. Solenidades em dia de semana
(ex.: Corpus Christi numa quinta) não são detectadas aqui — fase 2.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.missa import Missa
from app.models.usuario import Usuario
from app.services.email_sender import enviar_email

logger = logging.getLogger(__name__)

_ARQRIO = "https://www.arqrio.com.br/app/painel/amissa/amissa.pdf"
_MIRROR = "https://www.loreto.org.br/folheto-da-missa/"


def _proximo_domingo(hoje: date) -> date:
    """Próximo domingo; se hoje já é domingo, retorna hoje. (Mon=0 … Sun=6)"""
    return hoje + timedelta(days=(6 - hoje.weekday()) % 7)


def _destinatarios(db) -> list[tuple[str, str]]:
    admins = db.query(Usuario).filter(Usuario.is_admin.is_(True)).all()
    dest = [(u.email, u.nome or "admin") for u in admins if u.email]
    extra = getattr(settings, "ADMIN_EMAIL", None)
    if extra and all(extra != e for e, _ in dest):
        dest.append((extra, "admin"))
    return dest


def alertar_folheto_faltando() -> dict:
    """Verifica o domingo iminente; alerta admins por e-mail se não houver missa."""
    db = SessionLocal()
    try:
        domingo = _proximo_domingo(date.today())
        missa = db.query(Missa).filter(
            Missa.data == domingo,
            Missa.status_processamento == "concluido",
        ).first()
        if missa:
            return {"status": "ok", "domingo": domingo.isoformat(), "tem_missa": True}

        dest = _destinatarios(db)
        if not dest:
            logger.warning("Folheto de %s ausente, mas nenhum admin p/ alertar", domingo)
            return {"status": "sem_destinatario", "domingo": domingo.isoformat()}

        dstr = domingo.strftime("%d/%m/%Y")
        assunto = f"⚠️ Folheto de {dstr} ainda sem missa no Dia de Missa"
        app_url = getattr(settings, "APP_URL", None) or "https://diademissa.com.br"
        texto = (
            f"Atenção: o domingo {dstr} ainda NÃO tem missa montada no app.\n\n"
            "A fonte do arqrio é rotativa e some quando a semana passa — recupere "
            "o folheto manualmente enquanto está no ar:\n"
            f"- arqrio (atual): {_ARQRIO}\n"
            f"- mirror por data (Loreto): {_MIRROR}\n\n"
            f"App: {app_url}"
        )
        html = (
            '<div style="font-family:-apple-system,sans-serif;max-width:520px;margin:auto;padding:24px">'
            f'<h2 style="color:#B00020">⚠️ Folheto de {dstr} ainda sem missa</h2>'
            f'<p>O domingo <strong>{dstr}</strong> ainda <strong>não tem missa montada</strong> no Dia de Missa.</p>'
            '<p>A fonte do arqrio é rotativa e some quando a semana passa — vale recuperar '
            'o folheto manualmente enquanto está no ar:</p>'
            f'<ul><li><a href="{_ARQRIO}">Folheto atual (arqrio)</a></li>'
            f'<li><a href="{_MIRROR}">Mirror por data (Loreto)</a></li></ul>'
            f'<p><a href="{app_url}">Abrir o app</a></p></div>'
        )
        enviados = sum(1 for email, _nome in dest if enviar_email(email, assunto, html, texto))
        logger.info("Alerta folheto faltando %s: %d/%d e-mails", domingo, enviados, len(dest))
        return {
            "status": "alertado",
            "domingo": domingo.isoformat(),
            "enviados": enviados,
            "destinatarios": len(dest),
        }
    except Exception as e:
        logger.exception("Falha no alerta de folheto faltando")
        return {"status": "erro", "motivo": str(e)}
    finally:
        db.close()
