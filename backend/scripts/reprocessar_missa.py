"""Reprocessa uma missa arquivada pelo pipeline de PRODUÇÃO, carregando o .env
COMPLETO (inclui ANTHROPIC_MODEL_MM=claude-sonnet-5, USAR_LLM_MULTIMODAL, USAR_GATE_PDF,
ANTHROPIC_API_KEY) — nunca depende de export manual, que já causou reprocesso em
Haiku por engano.

Uso:  .venv/bin/python scripts/reprocessar_missa.py YYYY-MM-DD [YYYY-MM-DD ...]
"""
from __future__ import annotations

import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)


def _carregar_env() -> None:
    """Carrega o .env do backend em os.environ (formato do systemd EnvironmentFile:
    KEY=VALUE por linha, valor pode ter espaços). Não sobrescreve o que já existe."""
    caminho = os.path.join(BACKEND, ".env")
    if not os.path.exists(caminho):
        return
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            linha = linha.rstrip("\n")
            if not linha or linha.lstrip().startswith("#") or "=" not in linha:
                continue
            k, v = linha.split("=", 1)
            k, v = k.strip(), v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            os.environ.setdefault(k, v)


_carregar_env()
os.environ.setdefault("USAR_LLM", "1")

from pathlib import Path  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.pipeline import processar_pdf  # noqa: E402
from app.pipeline.download import hash_pdf, CACHE_DIR  # noqa: E402
from app.services.persist_missa import persistir_missa  # noqa: E402


def reprocessar(ds: str) -> None:
    pdf = CACHE_DIR / "archive" / f"{ds}.pdf"
    if not pdf.exists():
        print(f"{ds}: PDF não arquivado ({pdf})")
        return
    conteudo = pdf.read_bytes()
    missa = processar_pdf(pdf)
    db = SessionLocal()
    try:
        m = persistir_missa(db, missa, pdf_hash=hash_pdf(conteudo),
                            fonte_url=settings.PDF_URL, pdf_bytes=conteudo)
        db.refresh(m)
        print(f"{ds} -> {m.status_processamento} | blocos={len(m.blocos)} | obs={(m.observacoes or '')[:80]!r}")
    finally:
        db.close()


if __name__ == "__main__":
    datas = sys.argv[1:]
    if not datas:
        print("uso: reprocessar_missa.py YYYY-MM-DD [YYYY-MM-DD ...]")
        sys.exit(2)
    print(f"[modelo montagem = {os.getenv('ANTHROPIC_MODEL_MM', os.getenv('ANTHROPIC_MODEL', 'haiku(default)'))}]")
    for ds in datas:
        reprocessar(ds)
