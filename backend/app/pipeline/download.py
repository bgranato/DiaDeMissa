from __future__ import annotations

import hashlib
from pathlib import Path

import httpx

PDF_URL = "https://www.arqrio.com.br/app/painel/amissa/amissa.pdf"
CACHE_DIR = Path("data/pdfs")
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
