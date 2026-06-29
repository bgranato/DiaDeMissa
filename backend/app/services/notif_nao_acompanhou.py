"""Job diário que notifica usuários que NÃO concluíram a missa do dia anterior.

Roda à noite. Para cada usuário ativo:
- Identifica a missa do dia anterior (date.today() - 1 dia) no BD
- Verifica se há HistoricoUsuario com percentual_lido = 100
- Se não → cria um Lembrete tipo "nao_acompanhada" com data_hora_alerta = agora
  (o lembrete fica visível pro usuário na próxima abertura do app)
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.models.missa import Missa
from app.models.usuario import HistoricoUsuario, Lembrete, Usuario

logger = logging.getLogger(__name__)


def gerar_notificacoes_nao_acompanhada() -> dict:
    """Cria lembretes pros usuários que não concluíram a missa de ontem.

    Idempotente: usa título único `Você não acompanhou a missa de {data}` —
    se já existe um lembrete com esse título pro usuário, não duplica.
    """
    db = SessionLocal()
    try:
        ontem = date.today() - timedelta(days=1)
        missa = db.query(Missa).filter(Missa.data == ontem).first()
        if not missa:
            logger.info("Sem missa registrada para %s — pulando notificações", ontem)
            return {"status": "sem_missa", "data": ontem.isoformat()}

        usuarios = db.query(Usuario).all()
        criados = 0
        titulo_unico = f"Você não acompanhou a missa de {ontem.isoformat()}"

        for u in usuarios:
            historico = db.query(HistoricoUsuario).filter(
                and_(
                    HistoricoUsuario.usuario_id == u.id,
                    HistoricoUsuario.missa_id == missa.id,
                ),
            ).first()
            if historico and (historico.percentual_lido or 0) >= 100:
                continue  # já concluiu

            # Idempotência por (usuário, missa, tipo) — NÃO por título.
            # O título mudava de formato e deixava duplicatas passarem; a chave
            # real é "esse usuário já tem o aviso de não-acompanhou desta missa?".
            existente = db.query(Lembrete).filter(
                and_(
                    Lembrete.usuario_id == u.id,
                    Lembrete.missa_id == missa.id,
                    Lembrete.tipo == "nao_acompanhada",
                ),
            ).first()
            if existente:
                continue

            nota = (
                f"A celebração de {missa.celebracao or 'ontem'} ficou no histórico. "
                "Toque pra revisar quando quiser."
            )
            # Savepoint por inserção: se outro processo criar o mesmo lembrete ao
            # mesmo tempo, o índice único parcial dispara IntegrityError e nós
            # ignoramos SÓ aquela linha, sem abortar o lote inteiro.
            try:
                with db.begin_nested():
                    db.add(Lembrete(
                        usuario_id=u.id,
                        missa_id=missa.id,
                        titulo=titulo_unico,
                        nota=nota,
                        data_hora_alerta=datetime.now(timezone.utc),
                        minutos_antecedencia=0,
                        tipo="nao_acompanhada",
                        remetente="Dia de Missa",
                        ativo=True,
                    ))
                criados += 1
            except IntegrityError:
                logger.info("Lembrete já existia (corrida) p/ usuário %s, missa %s — ignorado", u.id, missa.id)

        db.commit()
        logger.info("Notificações 'não acompanhou' criadas: %d (missa %s)", criados, ontem)
        return {
            "status": "ok",
            "data_missa": ontem.isoformat(),
            "missa_id": missa.id,
            "notificacoes_criadas": criados,
        }
    except Exception as e:
        logger.exception("Falha ao gerar notificações nao_acompanhada")
        db.rollback()
        return {"status": "erro", "motivo": str(e)}
    finally:
        db.close()
