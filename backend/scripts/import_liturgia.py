"""One-shot: importa liturgia diária da Canção Nova para hoje + próximos N dias.

Uso:
    python3 scripts/import_liturgia.py            # hoje + 7 dias
    python3 scripts/import_liturgia.py 30         # hoje + 30 dias
    python3 scripts/import_liturgia.py 0          # só hoje
"""
from __future__ import annotations

import logging
import sys
from datetime import date, timedelta

from app.core.database import SessionLocal
from app.services.scraper_cancaonova import buscar_liturgia
from app.services.persist_liturgia import persistir_liturgia_diaria

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def main(dias: int = 7):
    db = SessionLocal()
    try:
        hoje = date.today()
        sucesso = 0
        falhas = 0
        for delta in range(dias + 1):
            data = hoje + timedelta(days=delta)
            log.info("Buscando liturgia de %s ...", data)
            dados = buscar_liturgia(data)
            if not dados:
                log.warning("  ✗ Falha (sem dados)")
                falhas += 1
                continue
            try:
                missa = persistir_liturgia_diaria(db, dados)
                log.info("  ✓ id=%d %s (cor=%s)", missa.id, dados.get("titulo", "?")[:60], dados.get("cor_liturgica"))
                sucesso += 1
            except Exception:
                log.exception("Erro persistindo %s", data)
                falhas += 1
        log.info("=" * 60)
        log.info("Sucesso: %d | Falhas: %d", sucesso, falhas)
        log.info("=" * 60)
    finally:
        db.close()


if __name__ == "__main__":
    dias = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    main(dias=dias)
