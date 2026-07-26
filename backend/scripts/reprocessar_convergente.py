"""Roda o fluxo 'montagem com conferência convergente' (passos 3–7) numa ou mais
missas, a partir do PDF arquivado. Carrega o .env COMPLETO (Sonnet/OpenRouter/gate).

Uso: .venv/bin/python scripts/reprocessar_convergente.py YYYY-MM-DD [YYYY-MM-DD ...]
"""
from __future__ import annotations

import json
import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)


def _carregar_env() -> None:
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
os.environ.setdefault("USAR_LLM_MULTIMODAL", "1")

from app.core.database import SessionLocal          # noqa: E402
from app.pipeline.download import CACHE_DIR          # noqa: E402
from app.pipeline.extract import extrair_texto_estruturado  # noqa: E402
from app.pipeline.clean import limpar                # noqa: E402
from app.services.publicacao_convergente import montar_e_publicar  # noqa: E402


def rodar(ds: str) -> None:
    pdf = CACHE_DIR / "archive" / f"{ds}.pdf"
    if not pdf.exists():
        print(f"{ds}: PDF não arquivado ({pdf})"); return
    conteudo = pdf.read_bytes()
    texto = limpar(extrair_texto_estruturado(pdf))
    db = SessionLocal()
    try:
        res = montar_e_publicar(db, ds, conteudo, texto)
        print("RESULTADO:", json.dumps({k: v for k, v in res.items() if k != "divergencias_restantes"}, ensure_ascii=False))
        divs = res.get("divergencias_restantes") or []
        if divs:
            print("  divergências restantes:", json.dumps(divs, ensure_ascii=False)[:600])
    finally:
        db.close()


if __name__ == "__main__":
    datas = sys.argv[1:]
    if not datas:
        print("uso: reprocessar_convergente.py YYYY-MM-DD [...]"); sys.exit(2)
    print(f"[modelos] mapa={os.getenv('MODELO_MAPA') or os.getenv('ANTHROPIC_MODEL_MM')} "
          f"montagem={os.getenv('ANTHROPIC_MODEL_MM')} conferente={os.getenv('MODELO_CONFERENTE') or os.getenv('ANTHROPIC_MODEL_MM')} "
          f"openrouter={'sim' if os.getenv('OPENROUTER_API_KEY') else 'não'}")
    for ds in datas:
        rodar(ds)
