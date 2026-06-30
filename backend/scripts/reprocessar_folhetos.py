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

import json  # noqa: E402
import sqlite3  # noqa: E402
import types  # noqa: E402

from app.pipeline import processar_pdf  # noqa: E402
from app.pipeline.download import hash_pdf, CACHE_DIR  # noqa: E402
from app.pipeline.extract import extrair_texto_estruturado  # noqa: E402
from app.pipeline.clean import limpar  # noqa: E402
from app.pipeline.structure_llm import _corrigir_posicao_refrao  # noqa: E402
from app.services.persist_missa import persistir_missa  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.config import settings  # noqa: E402

CUSTO_POR_FOLHETO = 0.07  # estimativa Haiku (~US$); só para o aviso do dry-run


def _db_path() -> str:
    """Caminho do arquivo SQLite a partir do DATABASE_URL (sqlite:///...)."""
    url = settings.DATABASE_URL
    return url[len("sqlite:///"):] if url.startswith("sqlite:///") else url


def modo_so_refrao(pdfs, dry_run: bool) -> int:
    """Recalcula posicao_refrao_apos dos cantos SEM LLM (custo US$ 0,00).

    Para cada PDF: re-extrai/limpa o texto, carrega os cantos JÁ SALVOS no banco,
    roda _corrigir_posicao_refrao (determinístico) e persiste APENAS o campo
    posicao_refrao_apos (dentro de conteudo_estruturado) dos cantos que mudaram.
    """
    con = sqlite3.connect(_db_path())
    con.row_factory = sqlite3.Row
    total_alt = 0
    for i, p in enumerate(pdfs, 1):
        data = p.stem  # nome do arquivo = AAAA-MM-DD
        try:
            texto_limpo = limpar(extrair_texto_estruturado(p))
        except Exception as e:  # noqa: BLE001
            print(f"[{i}/{len(pdfs)}] {p.name} · ERRO extração: {str(e)[:120]}")
            continue
        row_m = con.execute("SELECT id FROM missas WHERE data=?", (data,)).fetchone()
        if not row_m:
            print(f"[{i}/{len(pdfs)}] {data} · (não está no banco — pulando)")
            continue
        cantos = []
        for r in con.execute(
            "SELECT id, ordem, titulo, conteudo_estruturado FROM blocos_liturgicos "
            "WHERE missa_id=? AND tipo='canto' ORDER BY ordem", (row_m["id"],)
        ):
            ce = json.loads(r["conteudo_estruturado"] or "{}")
            stub = types.SimpleNamespace(
                tipo="canto",
                refrao=ce.get("refrao") or [],
                estrofes=ce.get("estrofes") or [],
                posicao_refrao_apos=ce.get("posicao_refrao_apos"),
            )
            cantos.append((r, ce, stub))
        antes = {id(s): s.posicao_refrao_apos for _, _, s in cantos}
        _corrigir_posicao_refrao(types.SimpleNamespace(blocos=[s for _, _, s in cantos]), texto_limpo)
        print(f"[{i}/{len(pdfs)}] {data} ({len(cantos)} cantos):")
        for r, ce, stub in cantos:
            b = antes[id(stub)]
            a = stub.posicao_refrao_apos
            marca = "→ ALTERA" if b != a else "  ok"
            print(f"    {(r['titulo'] or '')[:28]:<28} p{b} → p{a}   {marca}")
            if b != a:
                total_alt += 1
                if not dry_run:
                    ce["posicao_refrao_apos"] = a
                    con.execute(
                        "UPDATE blocos_liturgicos SET conteudo_estruturado=? WHERE id=?",
                        (json.dumps(ce, ensure_ascii=False), r["id"]),
                    )
    if not dry_run:
        con.commit()
    con.close()
    pref = "[dry-run] (nada gravado) " if dry_run else ""
    print(f"\n{pref}Cantos com posição alterada: {total_alt}. Custo: US$ 0,00 (sem LLM).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="só conta e estima custo")
    ap.add_argument("--limit", type=int, default=0, help="processa só os N primeiros (0=todos)")
    ap.add_argument("--dir", default=None, help="pasta dos PDFs (default: CACHE_DIR/archive)")
    ap.add_argument("--data", default=None, help="processa só o folheto dessa data (ex.: 2026-05-24)")
    ap.add_argument("--so-refrao", action="store_true",
                    help="SEM LLM (custo US$0): só recalcula posicao_refrao_apos dos cantos no banco")
    args = ap.parse_args()

    base = Path(args.dir) if args.dir else (CACHE_DIR / "archive")
    if not base.exists():
        print(f"Pasta não encontrada: {base}")
        return 1
    pdfs = sorted(base.glob("*.pdf"))
    if args.data:
        pdfs = [p for p in pdfs if args.data in p.name]
    if args.limit:
        pdfs = pdfs[:args.limit]

    if args.so_refrao:
        print(f"Pasta: {base}")
        print(f"PDFs: {len(pdfs)} · modo=SÓ REFRÃO (sem LLM){' · DRY-RUN' if args.dry_run else ''}")
        return modo_so_refrao(pdfs, args.dry_run)

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
