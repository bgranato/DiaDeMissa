from __future__ import annotations

from pathlib import Path

import fitz


def extrair_texto_estruturado(pdf_path: str | Path) -> str:
    doc = fitz.open(str(pdf_path))
    linhas_finais: list[str] = []

    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            for line in block.get("lines", []):
                texto_linha = ""
                ultimo_span = None
                for span in line["spans"]:
                    if ultimo_span:
                        gap = span["bbox"][0] - ultimo_span["bbox"][2]
                        if gap > 0.25 * ultimo_span["size"]:
                            if not texto_linha.endswith(" "):
                                texto_linha += " "
                    texto_linha += span["text"]
                    ultimo_span = span
                if texto_linha.strip():
                    linhas_finais.append(texto_linha.strip())

    doc.close()
    return "\n".join(linhas_finais)
