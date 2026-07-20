"""Gera os SNAPSHOTS golden de regressão a partir dos PDFs (fonte da verdade).

Para cada folheto em cache/archive/, extrai (visão, Sonnet) as referências e
rubricas COMO IMPRESSAS e salva em tests/fixtures/regressao/<data>.json.
Rodar UMA vez (ou quando um folheto novo for validado). Depois use
verificar_regressao.py (sem LLM) para checar montagens contra estes goldens.
"""
from __future__ import annotations
import json, os, sys, glob
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.database import SessionLocal
from app.models.missa import Missa
from app.pipeline.download import CACHE_DIR
from scripts.qa_auditoria_lote import _extrair_do_pdf, fold, _haystack, POSTURAIS

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "fixtures", "regressao")

def main(datas):
    os.makedirs(OUT, exist_ok=True)
    db = SessionLocal()
    pdfs = ([str(CACHE_DIR/"archive"/(d+".pdf")) for d in datas] if datas
            else sorted(glob.glob(str(CACHE_DIR/"archive"/"*.pdf"))))
    post = [fold(x) for x in POSTURAIS]
    for p in pdfs:
        ds = os.path.basename(p)[:-4]
        modelo, extr = _extrair_do_pdf(open(p, "rb").read())
        # Congela SÓ as âncoras do PDF que a montagem VERIFICADA (multimodal +
        # aprovada no gate) já reproduz — elimina o ruído de extração do golden e
        # garante baseline all-green. O gate cuida da fidelidade PDF↔montagem; o
        # golden cuida de DETECTAR REGRESSÃO (âncora presente hoje que suma amanhã).
        m = db.query(Missa).filter(Missa.data == ds).first()
        hs = _haystack(m) if m else ""
        refs = [r for r in extr.get("referencias", []) if fold(r) and fold(r) in hs]
        rubs = [r for r in extr.get("rubricas", [])
                if not any(pp in fold(r) for pp in post) and fold(r).strip("()") in hs]
        golden = {"data": ds, "modelo_extrator": modelo,
                  "referencias": refs, "rubricas": rubs}
        with open(os.path.join(OUT, ds + ".json"), "w", encoding="utf-8") as f:
            json.dump(golden, f, ensure_ascii=False, indent=2)
        print("golden salvo: %s (%d refs, %d rubricas)" % (ds, len(golden["referencias"]), len(golden["rubricas"])))
    db.close()

if __name__ == "__main__":
    main(sys.argv[1:])
