import hashlib
from pathlib import Path
from typing import Optional

import httpx

from app.core.config import settings


def baixar_pdf(url: str = None) -> bytes:
    url = url or settings.PDF_URL
    timeout = httpx.Timeout(settings.PDF_DOWNLOAD_TIMEOUT)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.content


def calcular_hash(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()


def salvar_pdf(conteudo: bytes, data_str: str) -> Path:
    cache_dir = Path(settings.PDF_CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)
    caminho = cache_dir / f"missa_{data_str}.pdf"
    caminho.write_bytes(conteudo)
    return caminho


def pdf_foi_alterado(novo_hash: str, hash_anterior: Optional[str]) -> bool:
    if hash_anterior is None:
        return True
    return novo_hash != hash_anterior
