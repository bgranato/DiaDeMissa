"""Job semanal: re-scrape Arquidiocese RJ + atualiza igrejas alteradas.

Mantém o catálogo local sempre atual. Atualização incremental:
- Itera todas as paróquias da Arquidiocese
- Pra cada local de culto, busca no BD por `arqrio_local_id`
- Se existe e algum campo mudou (endereço, telefone, lat/lng, etc.) → atualiza
- Se não existe → insere
- Também atualiza horários de missa via ajaxExibeAtividadesLocal

Roda semanalmente (segunda 4h via scheduler).
"""
from __future__ import annotations

import logging

from app.core.database import SessionLocal
from app.models.igreja import Igreja
from app.api.routes import _eh_mesma_igreja
from app.services.scraper_arqrio import iterar_todos_locais, buscar_horarios_local

logger = logging.getLogger(__name__)


def atualizar_catalogo_igrejas() -> dict:
    """Re-scrape Arquidiocese e atualiza catálogo incrementalmente.

    Returns dict com {inseridas, atualizadas, sem_alteracao, processados}.
    """
    logger.info("Iniciando atualização do catálogo de igrejas (Arquidiocese RJ)")
    db = SessionLocal()
    inseridas = 0
    atualizadas = 0
    sem_alteracao = 0
    sem_coords = 0
    horarios_atualizados = 0
    total = 0
    try:
        existentes = db.query(Igreja).all()

        for local in iterar_todos_locais():
            total += 1
            if local.get("lat") is None or local.get("lng") is None:
                sem_coords += 1
                continue

            # Match preferencial por arqrio_local_id (mais confiável)
            existente = None
            if local.get("arqrio_local_id"):
                existente = next((e for e in existentes if e.arqrio_local_id == local["arqrio_local_id"]), None)
            # Fallback: match por raiz de nome + proximidade ≤200m
            if not existente:
                existente = next(
                    (e for e in existentes if _eh_mesma_igreja(e, local["nome"], local.get("lat"), local.get("lng"))),
                    None,
                )

            campos = {
                "nome": local["nome"],
                "endereco": local.get("endereco"),
                "cidade": local.get("cidade") or "Rio de Janeiro",
                "estado": local.get("estado") or "RJ",
                "cep": local.get("cep"),
                "telefone": local.get("telefone"),
                "lat": local["lat"],
                "lng": local["lng"],
                "arqrio_local_id": local.get("arqrio_local_id"),
                "observacoes": f"Arquidiocese RJ · {local.get('paroquia', '')}".strip(" ·"),
            }

            if existente:
                mudou = False
                for k, v in campos.items():
                    if v and getattr(existente, k, None) != v:
                        setattr(existente, k, v)
                        mudou = True
                if mudou:
                    atualizadas += 1
                else:
                    sem_alteracao += 1
                igreja_obj = existente
            else:
                igreja_obj = Igreja(**campos)
                db.add(igreja_obj)
                existentes.append(igreja_obj)
                inseridas += 1

            # Atualiza horários de missa também
            if local.get("arqrio_local_id"):
                novos_horarios = buscar_horarios_local(local["arqrio_local_id"])
                if novos_horarios and novos_horarios != igreja_obj.horarios_missa:
                    igreja_obj.horarios_missa = novos_horarios
                    horarios_atualizados += 1

            # Commit incremental a cada 50
            if total % 50 == 0:
                db.commit()
                logger.info(
                    "Progresso: %d processados | inseridas=%d atualizadas=%d horarios=%d",
                    total, inseridas, atualizadas, horarios_atualizados,
                )

        db.commit()
    finally:
        db.close()

    resultado = {
        "processados": total,
        "inseridas": inseridas,
        "atualizadas": atualizadas,
        "sem_alteracao": sem_alteracao,
        "sem_coords": sem_coords,
        "horarios_atualizados": horarios_atualizados,
    }
    logger.info("Atualização do catálogo concluída: %s", resultado)
    return resultado
