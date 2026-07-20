"""Verifica REGRESSÃO: a montagem atual (no banco) ainda contém tudo que o
golden (extraído do PDF) exige? SEM LLM — rápido e determinístico.

Uso: .venv/bin/python scripts/verificar_regressao.py [YYYY-MM-DD ...]
Retorna código !=0 se houver regressão (útil para CI/pré-deploy).
"""
from __future__ import annotations
import json, os, sys, glob
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.database import SessionLocal
from app.models.missa import Missa
from scripts.qa_auditoria_lote import fold, _haystack, POSTURAIS

GOLDEN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "fixtures", "regressao")

def verificar(m, golden):
    hs = _haystack(m)
    post = [fold(x) for x in POSTURAIS]
    refs = [r for r in golden.get("referencias", []) if fold(r) and fold(r) not in hs]
    rub = [r for r in golden.get("rubricas", [])
           if not any(pp in fold(r) for pp in post) and fold(r).strip("()") not in hs]
    return refs, rub

def main(datas):
    db = SessionLocal()
    arquivos = ([os.path.join(GOLDEN, d+".json") for d in datas] if datas
                else sorted(glob.glob(os.path.join(GOLDEN, "*.json"))))
    total_reg = 0
    print("### VERIFICAÇÃO DE REGRESSÃO (montagem atual × golden) ###\n")
    for a in arquivos:
        if not os.path.exists(a):
            print("golden ausente: %s" % a); continue
        golden = json.load(open(a, encoding="utf-8"))
        ds = golden["data"]
        m = db.query(Missa).filter(Missa.data == ds).first()
        if not m:
            print("%s: sem missa no banco" % ds); continue
        refs, rub = verificar(m, golden)
        if refs or rub:
            total_reg += 1
            print("❌ %s REGREDIU -> refs faltando: %s | rubricas faltando: %s" % (ds, refs, rub))
        else:
            print("✅ %s ok" % ds)
    db.close()
    print("\nRegressões: %d" % total_reg)
    sys.exit(1 if total_reg else 0)

if __name__ == "__main__":
    main(sys.argv[1:])
