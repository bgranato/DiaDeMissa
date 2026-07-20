"""One-shot: importa horários de missa de cada igreja vinculada à Arquidiocese RJ.

Itera todas as Igrejas com `arqrio_local_id` setado e busca via
`ajaxExibeAtividadesLocal.php?id={local_id}`, salvando o resultado em
`horarios_missa` (formato compacto: "Dom: 7h, 9h, 11h | Seg: 19h | ...").

Uso:
    python3 scripts/import_horarios.py          # processa todos
    python3 scripts/import_horarios.py --only-missing  # só onde horarios_missa é null
"""
from __future__ import annotations

import logging
import sys

from app.core.database import SessionLocal
from app.models.igreja import Igreja
from app.services.scraper_arqrio import buscar_horarios_local

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def main(only_missing: bool = False):
    db = SessionLocal()
    try:
        q = db.query(Igreja).filter(Igreja.arqrio_local_id.isnot(None))
        if only_missing:
            q = q.filter((Igreja.horarios_missa.is_(None)) | (Igreja.horarios_missa == ""))
        igrejas = q.all()
        log.info("Igrejas a processar: %d", len(igrejas))

        com_horario = 0
        sem_horario = 0
        for i, ig in enumerate(igrejas, 1):
            horarios = buscar_horarios_local(ig.arqrio_local_id)
            if horarios:
                ig.horarios_missa = horarios
                com_horario += 1
                log.info("  ✓ id=%d %s → %s", ig.id, ig.nome[:50], horarios)
            else:
                sem_horario += 1
            if i % 25 == 0:
                db.commit()
                log.info("Progresso: %d/%d (com=%d sem=%d)", i, len(igrejas), com_horario, sem_horario)
        db.commit()
        log.info("=" * 60)
        log.info("Com horário:    %d", com_horario)
        log.info("Sem horário:    %d", sem_horario)
        log.info("Total:          %d", len(igrejas))
        log.info("=" * 60)
    finally:
        db.close()


if __name__ == "__main__":
    only_miss = "--only-missing" in sys.argv
    main(only_missing=only_miss)
