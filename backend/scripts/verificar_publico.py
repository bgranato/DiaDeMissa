"""Verificador de correção SEMPRE contra a API PÚBLICA (nunca banco local).

Regra aprendida (falha de verificação 2x): verificar em banco local, por ocorrência
parcial, ou com 1 request só (que pode cair num worker com pool de conexão stale —
prod roda --workers 2 + journal_mode=delete) NÃO é confiável. Este script:
  - bate N vezes na API pública (default 25) para pegar qualquer worker stale;
  - varre TODOS os campos string do bloco (não só estrofes[-1]);
  - imprime o JSON BRUTO do campo exato para colar no relatório.

Uso: python scripts/verificar_publico.py YYYY-MM-DD "canto final" [N]
Sai com código 1 se QUALQUER request trouxer órfão de número de estrofe.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request

BASE = "https://diademissa.com.br/api/v1/missa/por-data/"
PAT = re.compile(r"\s\d{1,2}\.\s*$")  # " 2." / " 3." grudado no fim de um verso


def _get(data_iso: str) -> dict:
    req = urllib.request.Request(
        BASE + data_iso, headers={"Cache-Control": "no-cache"}
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def _bloco(d: dict, titulo: str):
    for b in d.get("blocos") or []:
        if (b.get("titulo") or "").lower().strip() == titulo.lower().strip():
            return b
    return None


def _orfaos(o, path="") -> list:
    achados = []
    if isinstance(o, str):
        if PAT.search(o):
            achados.append((path, o[-40:]))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            achados += _orfaos(v, f"{path}[{i}]")
    elif isinstance(o, dict):
        for k, v in o.items():
            achados += _orfaos(v, f"{path}.{k}")
    return achados


def main() -> int:
    if len(sys.argv) < 3:
        print("uso: verificar_publico.py YYYY-MM-DD \"titulo do bloco\" [N]")
        return 2
    data_iso, titulo = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 25

    ruins = 0
    for _ in range(n):
        b = _bloco(_get(data_iso), titulo)
        if b and _orfaos(b, titulo):
            ruins += 1
    print(f"{n} GETs públicos — com órfão: {ruins}")

    b = _bloco(_get(data_iso), titulo)
    if not b:
        print(f"bloco {titulo!r} não encontrado em {data_iso}")
        return 1
    print("JSON BRUTO (último item de cada estrofe):")
    for i, e in enumerate(b.get("estrofes") or []):
        print(f"  estrofe {i+1} [len={len(e)}]: {json.dumps(e[-1], ensure_ascii=False)}")
    return 1 if ruins else 0


if __name__ == "__main__":
    sys.exit(main())
