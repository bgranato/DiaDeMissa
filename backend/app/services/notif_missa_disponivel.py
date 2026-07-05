"""Alerta por e-mail: avisa os usuários (que não desativaram) quando uma nova
missa (folheto) entra no sistema. Envia no máximo 1 vez por missa.

Opt-OUT: por padrão todo cadastrado recebe; quem não quiser desativa no Perfil
(preferencia alerta_missa_email=False).
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.missa import Missa
from app.models.usuario import Usuario, PreferenciaUsuario
from app.services.email_sender import enviar_email_missa_disponivel

logger = logging.getLogger(__name__)

_MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def _data_extenso(d) -> str:
    return f"{d.day} de {_MESES[d.month - 1]} de {d.year}"


def notificar_missa_disponivel(db: Session, missa: Missa) -> dict:
    """Envia o alerta 'missa disponível' (1x por missa) aos usuários que NÃO
    desativaram. Best-effort: falha de envio não quebra o pipeline.
    """
    if missa is None:
        return {"enviados": 0, "motivo": "missa nula"}
    if missa.status_processamento != "concluido":
        return {"enviados": 0, "motivo": "missa não publicada"}
    if getattr(missa, "alerta_email_enviado", False):
        return {"enviados": 0, "motivo": "já enviado"}

    # Ativos, com e-mail, que NÃO desativaram. LEFT JOIN: quem ainda não tem linha
    # de preferências conta como opt-in (default True).
    usuarios = (
        db.query(Usuario)
        .outerjoin(PreferenciaUsuario, PreferenciaUsuario.usuario_id == Usuario.id)
        .filter(
            Usuario.email.isnot(None),
            (Usuario.status == "ativo") | (Usuario.status.is_(None)),
            (PreferenciaUsuario.alerta_missa_email.is_(True))
            | (PreferenciaUsuario.id.is_(None)),
        )
        .all()
    )

    data_str = _data_extenso(missa.data)
    celebracao = missa.celebracao or "Missa do dia"
    enviados = 0
    for u in usuarios:
        try:
            if enviar_email_missa_disponivel(u.email, u.nome or "", data_str, celebracao):
                enviados += 1
        except Exception:
            logger.exception("Falha ao enviar alerta de missa para %s", u.email)

    # Marca como enviado (evita reenvio). O disparo é por publicação da missa,
    # não retroativo — se o SMTP estiver off, novas missas avisam quando ligar.
    missa.alerta_email_enviado = True
    db.add(missa)
    db.commit()

    logger.info("Alerta 'missa disponível' %s: %d e-mail(s) enviados de %d elegíveis",
                missa.data, enviados, len(usuarios))
    return {"enviados": enviados, "elegiveis": len(usuarios)}
