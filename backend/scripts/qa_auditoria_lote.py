"""QA em lote: audita a fidelidade PDF × montagem de TODOS os folhetos arquivados.

Lê cada PDF em cache/archive/ (visão, Sonnet), extrai referências e rubricas
como IMPRESSAS, e compara com a montagem no banco. Imprime, por missa, o que
está faltando/errado — com a régua calibrada (dobra sem acento, preserva a
estrutura da referência, trata posturais à parte) para não inflar falsos.

Uso (no servidor, com ANTHROPIC_API_KEY no ambiente):
    .venv/bin/python scripts/qa_auditoria_lote.py [YYYY-MM-DD ...]

Sem argumentos, audita todos os PDFs de cache/archive/. Ferramenta de QA
sob demanda — não altera nada no banco.
"""
from __future__ import annotations

import base64
import glob
import json
import os
import re
import sys
import unicodedata
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.missa import Missa
from app.pipeline.download import CACHE_DIR

MODELS = [os.getenv("ANTHROPIC_MODEL_GATE", "claude-sonnet-5"), "claude-haiku-4-5-20251001"]
POSTURAIS = ("de pe", "sentado", "ajoelhado", "momento de silencio", "2x")

PROMPT = (
    "Você recebe o PDF OFICIAL de um folheto de missa. Extraia EXATAMENTE como "
    "impresso, sem inventar nem corrigir, um JSON com:\n"
    '- "referencias": TODAS as referências bíblicas/litúrgicas (entre parênteses/'
    'colchetes e as das Leituras da Semana).\n'
    '- "rubricas": TODAS as instruções entre parênteses que NÃO são referência '
    '(ex.: "(De pé)","(Sentados)","(Momento de silêncio)","(todos se inclinam...)",'
    '"(O Presidente continua)","(Outros pedidos)").\n'
    "Responda SOMENTE o JSON."
)


def _extrair_do_pdf(pdf_bytes: bytes):
    b64 = base64.standard_b64encode(pdf_bytes).decode()
    body = {"max_tokens": 4096, "messages": [{"role": "user", "content": [
        {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64}},
        {"type": "text", "text": PROMPT}]}]}
    last = None
    for modelo in MODELS:
        body["model"] = modelo
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
            headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                     "anthropic-version": "2023-06-01", "content-type": "application/json"})
        try:
            data = json.loads(urllib.request.urlopen(req, timeout=180).read())
            t = "".join(p.get("text", "") for p in data.get("content", []) if p.get("type") == "text")
            t = re.sub(r"^```json|^```|```$", "", t.strip(), flags=re.M).strip()
            return modelo, json.loads(t)
        except Exception as e:
            last = "%s: %s" % (modelo, e)
    raise RuntimeError(last)


def fold(s: str) -> str:
    # Dobra sem acento; mantém só letras/dígitos/HÍFEN. O hífen fica para
    # distinguir intervalo de citação ("ct31-4a" != "ct314a"); vírgula/ponto/
    # parênteses saem para casar variações de OCR ("2Rs, 17" == "2Rs 17").
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9\-]", "", s.lower())


def _haystack(m) -> str:
    parts = []
    for b in m.blocos:
        parts.append(b.titulo or "")
        parts.append(b.referencia or "")
        ce = b.conteudo_estruturado
        parts.append(ce if isinstance(ce, str) else json.dumps(ce, ensure_ascii=False))
    return fold(" ".join(parts))


def auditar(m, pdf_bytes: bytes):
    modelo, extr = _extrair_do_pdf(pdf_bytes)
    hs = _haystack(m)
    post = [fold(x) for x in POSTURAIS]
    refs = [r for r in extr.get("referencias", []) if fold(r) and fold(r) not in hs]
    rub = [r for r in extr.get("rubricas", [])
           if not any(pp in fold(r) for pp in post) and fold(r).strip("()") not in hs]
    return modelo, refs, rub


def main(datas):
    db = SessionLocal()
    pdfs = ([str(CACHE_DIR / "archive" / (d + ".pdf")) for d in datas] if datas
            else sorted(glob.glob(str(CACHE_DIR / "archive" / "*.pdf"))))
    print("### QA AUDITORIA EM LOTE — %d folheto(s) ###\n" % len(pdfs))
    resumo = {}
    for p in pdfs:
        ds = os.path.basename(p)[:-4]
        m = db.query(Missa).filter(Missa.data == ds).first()
        if not m:
            print("%s: sem missa no banco\n" % ds); continue
        modelo, refs, rub = auditar(m, open(p, "rb").read())
        resumo[ds] = (len(refs), len(rub))
        print("=== %s [%s] ===" % (ds, modelo))
        print("  refs faltando (%d): %s" % (len(refs), refs) if refs else "  ✅ referências: todas presentes")
        print("  rubricas faltando (%d): %s" % (len(rub), rub) if rub else "  ✅ rubricas não-posturais: todas presentes")
        print()
    print("### RESUMO (refs_faltando, rubricas_faltando) ###")
    for ds, (a, b) in resumo.items():
        print("  %s -> refs=%d rub=%d" % (ds, a, b))
    db.close()


if __name__ == "__main__":
    main(sys.argv[1:])
