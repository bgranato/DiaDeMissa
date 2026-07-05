"""Envio de e-mail via SMTP (Gmail por padrão).

Em dev (sem credenciais), apenas loga o conteúdo no console — útil pra copiar o
link de recuperação durante desenvolvimento.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def _smtp_configurado() -> bool:
    return bool(
        getattr(settings, "SMTP_HOST", None)
        and getattr(settings, "SMTP_USER", None)
        and getattr(settings, "SMTP_PASSWORD", None)
    )


def enviar_email(destinatario: str, assunto: str, corpo_html: str, corpo_texto: str | None = None) -> bool:
    """Envia e-mail. Retorna True se enviado via SMTP, False se só logado em dev."""
    if not _smtp_configurado():
        logger.warning(
            "SMTP não configurado — exibindo email em console:\n"
            "Para: %s\nAssunto: %s\n\n%s",
            destinatario, assunto, corpo_texto or corpo_html,
        )
        return False

    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
    msg["To"] = destinatario
    msg.set_content(corpo_texto or corpo_html)
    msg.add_alternative(corpo_html, subtype="html")

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT or 587) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("Email enviado para %s", destinatario)
        return True
    except Exception:
        logger.exception("Falha ao enviar e-mail para %s", destinatario)
        return False


def enviar_email_recuperacao(destinatario: str, nome: str, link: str) -> bool:
    assunto = "Recuperação de senha - Dia de Missa"
    texto = (
        f"Olá, {nome}.\n\n"
        f"Recebemos um pedido para redefinir sua senha no Dia de Missa.\n"
        f"Use o link abaixo (válido por 1 hora):\n\n{link}\n\n"
        f"Se você não fez esta solicitação, ignore este e-mail."
    )
    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: auto; padding: 24px;">
      <h2 style="color: #1A2B4C;">Olá, {nome}</h2>
      <p>Recebemos um pedido para redefinir sua senha no <strong>Dia de Missa</strong>.</p>
      <p>Clique no botão abaixo para criar uma nova senha (link válido por 1 hora):</p>
      <p style="text-align: center; margin: 32px 0;">
        <a href="{link}" style="background: #1A2B4C; color: #F9F9F9; padding: 12px 24px; text-decoration: none; border-radius: 12px; font-weight: bold;">
          Redefinir senha
        </a>
      </p>
      <p style="color: #888; font-size: 12px;">Se você não fez esta solicitação, ignore este e-mail.</p>
    </div>
    """
    return enviar_email(destinatario, assunto, html, texto)


def enviar_email_missa_disponivel(destinatario: str, nome: str, data_str: str, celebracao: str) -> bool:
    """Avisa que a missa do dia já está disponível no app."""
    assunto = f"A missa de {data_str} já está disponível - Dia de Missa"
    app_url = getattr(settings, "APP_URL", None) or "https://diademissa.com.br"
    texto = (
        f"Olá, {nome}.\n\n"
        f"A missa de {data_str} — {celebracao} — já está disponível no Dia de Missa.\n"
        f"Acesse para acompanhar: {app_url}\n\n"
        f"Se não quiser mais receber estes avisos, é só desativar em Perfil › Notificações."
    )
    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: auto; padding: 24px;">
      <h2 style="color: #1A2B4C;">Olá, {nome}</h2>
      <p>A missa de <strong>{data_str}</strong> — {celebracao} — já está disponível no <strong>Dia de Missa</strong>.</p>
      <p style="text-align: center; margin: 32px 0;">
        <a href="{app_url}" style="background: #1A2B4C; color: #F9F9F9; padding: 12px 24px; text-decoration: none; border-radius: 12px; font-weight: bold;">
          Acompanhar a missa
        </a>
      </p>
      <p style="color: #888; font-size: 12px;">Se não quiser mais receber estes avisos, desative em Perfil › Notificações.</p>
    </div>
    """
    return enviar_email(destinatario, assunto, html, texto)
