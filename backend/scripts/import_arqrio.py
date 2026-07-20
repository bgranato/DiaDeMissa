"""One-shot: importa todo o catálogo de paróquias e locais de culto da Arquidiocese RJ.

Roda direto contra o BD (sem HTTP/auth). Para locais que já existem (raiz de nome igual +
coords próximas), atualiza com os dados oficiais. Senão, insere.

Uso:
    python3 scripts/import_arqrio.py            # importa tudo (~5min)
    python3 scripts/import_arqrio.py --dry-run  # só imprime, não grava
"""
from __future__ import annotations

import logging
import sys

from app.core.database import SessionLocal
from app.models.igreja import Igreja
from app.api.routes import _eh_mesma_igreja
from app.services.scraper_arqrio import iterar_todos_locais

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def main(dry_run: bool = False):
    db = SessionLocal()
    try:
        existentes = db.query(Igreja).all()
        log.info("Catálogo atual: %d igrejas", len(existentes))

        inseridas = 0
        atualizadas = 0
        ignoradas = 0
        sem_coords = 0
        total_processados = 0

        for local in iterar_todos_locais():
            total_processados += 1
            if local.get("lat") is None or local.get("lng") is None:
                sem_coords += 1
                # Não importamos sem coords — busca por proximidade não funcionaria.
                # Reverse-geocode posterior pelo endereço pode resolver, mas pulamos por enquanto.
                continue

            # Procura duplicata: raiz de nome + ≤200m
            duplicata = None
            for e in existentes:
                if _eh_mesma_igreja(e, local["nome"], local["lat"], local["lng"]):
                    duplicata = e
                    break

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

            if duplicata:
                # Atualiza com dados oficiais (preferência por dados não-nulos da fonte oficial)
                mudou = False
                for k, v in campos.items():
                    if v and getattr(duplicata, k, None) != v:
                        setattr(duplicata, k, v)
                        mudou = True
                if mudou:
                    atualizadas += 1
                else:
                    ignoradas += 1
            else:
                nova = Igreja(**campos)
                if not dry_run:
                    db.add(nova)
                    existentes.append(nova)  # evita re-inserir no mesmo loop
                inseridas += 1

            # Commit incremental a cada 50 pra não perder progresso
            if not dry_run and total_processados % 50 == 0:
                db.commit()
                log.info(
                    "Progresso: %d processados | inseridas=%d atualizadas=%d sem_coords=%d",
                    total_processados, inseridas, atualizadas, sem_coords,
                )

        if not dry_run:
            db.commit()

        log.info("=" * 60)
        log.info("RESUMO IMPORT ARQUIDIOCESE RJ")
        log.info("Processados:      %d locais", total_processados)
        log.info("Inseridos:        %d", inseridas)
        log.info("Atualizados:      %d", atualizadas)
        log.info("Sem alteração:    %d", ignoradas)
        log.info("Pulados (s/coords): %d", sem_coords)
        log.info("Total no BD agora: %d", db.query(Igreja).count())
        log.info("=" * 60)
    finally:
        db.close()


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    main(dry_run=dry)
