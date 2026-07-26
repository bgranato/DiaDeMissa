from __future__ import annotations

import hashlib
import os
from pathlib import Path

import httpx

PDF_URL = "https://www.arqrio.com.br/app/painel/amissa/amissa.pdf"
# Cache de PDFs em path absoluto fora do diretório do app (writable, persistente,
# imune a deploy rsync --delete e a problemas transitórios de filesystem do app).
# Override via env DIADEMISSA_PDF_CACHE; em dev, default é ./data/pdfs (relativo).
_DEFAULT_CACHE = "/var/lib/diademissa/pdfs" if Path("/var/lib/diademissa").exists() else "data/pdfs"
CACHE_DIR = Path(os.environ.get("DIADEMISSA_PDF_CACHE", _DEFAULT_CACHE))
TIMEOUT = 30


def obter_pdf() -> bytes:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    timeout = httpx.Timeout(TIMEOUT)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resp = client.get(PDF_URL)
        resp.raise_for_status()
    return resp.content


def hash_pdf(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()
