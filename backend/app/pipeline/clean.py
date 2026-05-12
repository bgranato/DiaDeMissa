from __future__ import annotations

import re
import unicodedata


def limpar(texto: str) -> str:
    texto = unicodedata.normalize("NFC", texto)
    texto = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", texto)
    texto = re.sub(
        r"([a-záéíóúâêôãõçà,;:])\s*\n\s*([a-záéíóúâêôãõçà])",
        r"\1 \2",
        texto,
    )
    texto = re.sub(r"(\s|^)([PTLVR])\.([A-ZÁÉÍÓÚÂÊÔÃÕÇ])", r"\1\2. \3", texto)
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    texto = "\n".join(linha.strip() for linha in texto.split("\n"))
    return texto.strip()
