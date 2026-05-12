from __future__ import annotations
import io
import re
from dataclasses import dataclass, field
from typing import Optional

import pdfplumber


@dataclass
class FragmentoTexto:
    texto: str
    fonte: str = ""
    tamanho: float = 0
    negrito: bool = False
    italico: bool = False

    @property
    def estilo(self) -> str:
        if self.negrito and self.italico:
            return "bold-italic"
        if self.negrito:
            return "bold"
        if self.italico:
            return "italic"
        return "normal"


def extrair_fragmentos(conteudo_pdf: bytes) -> list[list[FragmentoTexto]]:
    paginas_fragmentos = []
    with pdfplumber.open(io.BytesIO(conteudo_pdf)) as pdf:
        for pagina in pdf.pages:
            palavras = pagina.extract_words(
                keep_blank_chars=False,
                x_tolerance=2,
                extra_attrs=["fontname", "size"],
            )
            fragmentos_pagina: list[FragmentoTexto] = []
            for w in palavras:
                fontname = w.get("fontname", "")
                size = w.get("size", 0)
                negrito = "Bold" in fontname or "bold" in fontname
                italico = "Italic" in fontname or "italic" in fontname or "Oblique" in fontname or "MediumItalic" in fontname
                fragmentos_pagina.append(FragmentoTexto(
                    texto=w["text"],
                    fonte=fontname,
                    tamanho=size,
                    negrito=negrito,
                    italico=italico,
                ))
            paginas_fragmentos.append(fragmentos_pagina)
    return paginas_fragmentos


def _limpar_linha(texto: str) -> str:
    text = texto.strip()
    if not text:
        return ""
    text = re.sub(r"  +", " ", text)
    return text


def _reconstruir_palavras(texto: str) -> str:
    palavras = texto.split()
    if len(palavras) < 3:
        return texto

    i = 0
    result = []
    while i < len(palavras):
        p = palavras[i]
        clean_p = "".join(c for c in p if c.isalpha())
        if clean_p and clean_p[0].isupper() and len(clean_p) <= 3:
            j = i + 1
            merged = clean_p
            while j < len(palavras):
                nxt = palavras[j]
                nxt_clean = "".join(c for c in nxt if c.isalpha())
                if nxt_clean and len(nxt_clean) <= 3 and nxt_clean[0].isupper():
                    merged += nxt_clean
                    j += 1
                elif nxt_clean and len(clean_p) == 1 and len(nxt_clean) > 1 and nxt_clean[0].islower():
                    # Single uppercase letter followed by lowercase word (e.g. "N" + "este" -> "Neste")
                    merged += nxt_clean
                    j += 1
                    break
                else:
                    break
            if len(merged) >= 5:
                last = palavras[j - 1]
                punct = "".join(c for c in last if not c.isalpha())
                result.append(merged + punct)
                i = j
                continue
        result.append(p)
        i += 1
    return " ".join(result)


@dataclass
class LinhaTexto:
    texto: str
    pagina: int
    x_top: float
    y_top: float
    fragmentos: list[FragmentoTexto] = field(default_factory=list)

    @property
    def texto_formatado(self) -> str:
        if not self.fragmentos:
            return self.texto
        partes: list[str] = []
        i = 0
        while i < len(self.fragmentos):
            f = self.fragmentos[i]
            if f.negrito:
                merged = [f.texto]
                i += 1
                while i < len(self.fragmentos) and self.fragmentos[i].negrito:
                    merged.append(self.fragmentos[i].texto)
                    i += 1
                partes.append(f"[[B]]{' '.join(merged)}[[/B]]")
            elif f.italico:
                merged = [f.texto]
                i += 1
                while i < len(self.fragmentos) and self.fragmentos[i].italico:
                    merged.append(self.fragmentos[i].texto)
                    i += 1
                partes.append(f"[[I]]{' '.join(merged)}[[/I]]")
            else:
                partes.append(f.texto)
                i += 1
        return " ".join(partes)


def extrair_texto(conteudo_pdf: bytes) -> list[LinhaTexto]:
    linhas: list[LinhaTexto] = []
    paginas_frags = extrair_fragmentos(conteudo_pdf)

    with pdfplumber.open(io.BytesIO(conteudo_pdf)) as pdf:
        for num_pagina, pagina in enumerate(pdf.pages, start=1):
            palavras = pagina.extract_words(
                keep_blank_chars=False,
                x_tolerance=2,
                extra_attrs=["fontname", "size"],
            )

            linhas_pagina: dict[int, list[tuple[float, str, str, float, bool, bool]]] = {}
            for w in palavras:
                y = int(w["top"])
                fontname = w.get("fontname", "")
                size = w.get("size", 0)
                negrito = "Bold" in fontname or "bold" in fontname
                italico = "Italic" in fontname or "italic" in fontname or "Oblique" in fontname or "MediumItalic" in fontname
                if y not in linhas_pagina:
                    linhas_pagina[y] = []
                linhas_pagina[y].append((w["x0"], w["text"], fontname, size, negrito, italico))

            for y in sorted(linhas_pagina.keys()):
                items = sorted(linhas_pagina[y], key=lambda p: p[0])
                texto_bruto = " ".join(it[1] for it in items)
                texto_limpo = _limpar_linha(texto_bruto)
                texto_limpo = _reconstruir_palavras(texto_limpo)
                if texto_limpo:
                    x_min = min(it[0] for it in items)
                    frags = [FragmentoTexto(texto=it[1], fonte=it[2], tamanho=it[3], negrito=it[4], italico=it[5]) for it in items]
                    linhas.append(LinhaTexto(
                        texto=texto_limpo,
                        pagina=num_pagina,
                        x_top=x_min,
                        y_top=float(y),
                        fragmentos=frags,
                    ))

    return linhas
