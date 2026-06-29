#!/usr/bin/env python3
"""Conserto dos lembretes 'não acompanhou' duplicados.

O que faz (idempotente — pode rodar quantas vezes quiser):
  1) Remove duplicatas existentes de lembretes tipo 'nao_acompanhada':
     para cada (usuario_id, missa_id), mantém o de MENOR id e apaga os demais.
  2) Cria o índice único PARCIAL que impede novas duplicatas
     (uq_lembrete_nao_acompanhada). Só afeta tipo='nao_acompanhada'; lembretes
     do usuário e broadcasts continuam podendo repetir.

Uso (a partir de backend/):
    python3 scripts/fix_lembretes_duplicados.py --dry-run   # só mostra o que faria
    python3 scripts/fix_lembretes_duplicados.py             # aplica

IMPORTANTE: em produção, faça backup do banco ANTES (veja docs/RUNBOOK_lembretes.md).
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text  # noqa: E402
from app.core.database import SessionLocal, engine  # noqa: E402
from app.models.usuario import Lembrete  # noqa: E402


def achar_duplicatas(db) -> list[int]:
    """IDs a apagar: tudo que não é o menor id de cada (usuario_id, missa_id)."""
    registros = (
        db.query(Lembrete)
        .filter(Lembrete.tipo == "nao_acompanhada")
        .order_by(Lembrete.id.asc())
        .all()
    )
    vistos: dict[tuple, int] = {}
    apagar: list[int] = []
    grupos = defaultdict(int)
    for r in registros:
        chave = (r.usuario_id, r.missa_id)
        grupos[chave] += 1
        if chave in vistos:
            apagar.append(r.id)   # já tem um menor → este é duplicata
        else:
            vistos[chave] = r.id
    return apagar


def criar_indice(db, dry_run: bool) -> None:
    ddl = (
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_lembrete_nao_acompanhada "
        "ON lembretes (usuario_id, missa_id) WHERE tipo = 'nao_acompanhada'"
    )
    if dry_run:
        print(f"[dry-run] criaria índice: {ddl}")
        return
    db.execute(text(ddl))
    db.commit()
    print("Índice único parcial criado (ou já existia).")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="só mostra, não altera")
    args = ap.parse_args()

    print(f"Banco: {engine.url.render_as_string(hide_password=True)}")
    db = SessionLocal()
    try:
        apagar = achar_duplicatas(db)
        print(f"Duplicatas de 'nao_acompanhada' encontradas: {len(apagar)}")
        if apagar and not args.dry_run:
            db.query(Lembrete).filter(Lembrete.id.in_(apagar)).delete(synchronize_session=False)
            db.commit()
            print(f"Apagadas {len(apagar)} duplicatas.")
        elif apagar:
            print(f"[dry-run] apagaria {len(apagar)} duplicatas (ids: {apagar[:20]}{'...' if len(apagar) > 20 else ''})")
        criar_indice(db, args.dry_run)
        print("OK.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
