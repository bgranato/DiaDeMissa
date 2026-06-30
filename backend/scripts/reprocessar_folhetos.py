#!/usr/bin/env python3
"""Backfill — reprocessa folhetos arquivados pelo pipeline atual (LLM se USAR_LLM=1).

Para cada PDF na pasta de arquivo (CACHE_DIR/archive), roda o pipeline e
RE-PERSISTE a missa (upsert por data, substituindo os blocos antigos). Útil para
remontar todas as missas passadas com a montagem por LLM e poder auditar.

Carrega o .env do backend (USAR_LLM, ANTHROPIC_*) — necessário porque a chave/flag
não vêm no ambiente de um `python` manual (só no systemd).

Uso (a partir de backend/):
    python3 scripts/reprocessar_folhetos.py --dry-run        # conta + estima custo
    python3 scripts/reprocessar_folhetos.py --limit 3        # processa só os 3 primeiros
    python3 scripts/reprocessar_folhetos.py                  # processa todos
    python3 scripts/reprocessar_folhetos.py --dir /caminho   # outra pasta de PDFs

IMPORTANTE: faça backup do banco antes de rodar sem --dry-run.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))


def _carregar_env() -> None:
    """Lê backend/.env e popula os.environ (sem sobrescrever o que já existe)."""
    env = BACKEND / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_carregar_env()

from app.pipeline import processar_pdf  # noqa: E402
from app.pipeline.download import hash_pdf, CACHE_DIR  # noqa: E402
from app.services.persist_missa import persistir_missa  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.config import settings  # noqa: E402

CUSTO_POR_FOLHETO = 0.07  # estimativa Haiku (~US$); só para o aviso do dry-run


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="só conta e estima custo")
    ap.add_argument("--limit", type=int, default=0, help="processa só os N primeiros (0=todos)")
    ap.add_argument("--dir", default=None, help="pasta dos PDFs (default: CACHE_DIR/archive)")
    args = ap.parse_args()

    base = Path(args.dir) if args.dir else (CACHE_DIR / "archive")
    if not base.exists():
        print(f"Pasta não encontrada: {base}")
        return 1
    pdfs = sorted(base.glob("*.pdf"))
    if args.limit:
        pdfs = pdfs[:args.limit]

    usar_llm = os.getenv("USAR_LLM", "0").lower() in ("1", "true", "yes", "on")
    print(f"Pasta: {base}")
    print(f"PDFs: {len(pdfs)} · USAR_LLM={usar_llm} · modelo={os.getenv('ANTHROPIC_MODEL', '(default)')}")

    if args.dry_run:
        custo = len(pdfs) * CUSTO_POR_FOLHETO if usar_llm else 0.0
        print(f"[dry-run] processaria {len(pdfs)} folhetos. "
              f"Custo estimado{' (LLM)' if usar_llm else ' (regex, sem custo)'}: ~US$ {custo:.2f}")
        for p in pdfs[:15]:
            print("  -", p.name)
        if len(pdfs) > 15:
            print(f"  ... (+{len(pdfs) - 15})")
        return 0

    ok = erros = pendentes = 0
    for i, p in enumerate(pdfs, 1):
        try:
            conteudo = p.read_bytes()
            h = hash_pdf(conteudo)
            missa_pyd = processar_pdf(p)
            db = SessionLocal()
            try:
                m = persistir_missa(db, missa_pyd, pdf_hash=h, fonte_url=settings.PDF_URL)
                status = m.status_processamento
            finally:
                db.close()
            if status == "pendente_revisao":
                pendentes += 1
                flag = "⚠ pendente_revisao"
            else:
                ok += 1
                flag = "ok"
            print(f"[{i}/{len(pdfs)}] {p.name} · {missa_pyd.data} · {len(missa_pyd.blocos)} blocos · {flag}")
        except Exception as e:
            erros += 1
            print(f"[{i}/{len(pdfs)}] {p.name} · ERRO: {str(e)[:160]}")

    print(f"\nResumo: {ok} ok · {pendentes} pendente_revisao · {erros} erro(s) de {len(pdfs)}")
    if pendentes:
        print("→ Os 'pendente_revisao' foram escondidos do app pelo auditor; revise-os.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
