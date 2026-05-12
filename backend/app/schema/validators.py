from __future__ import annotations
import re
from typing import Annotated

# Padrões proibidos em qualquer campo de texto
ARTEFATOS = [
    (r"\s/\s", "barra separadora não traduzida"),
    (r"^/|/$", "barra no início/fim"),
    (r"##|^\*\*|\*\*$", "markdown vazado"),
    (r"\w+-\s*\n", "hifenização de quebra de linha"),
    (r"[a-záéíóúâêôãõç][A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]", "palavras coladas (camelCase)"),
    (r"^\s*\d+\.\s", "numeração de estrofe dentro do texto"),
    (r"\(De pé\)|\(Sentados?\)|\(Ajoelhados?\)", "postura como texto"),
    (r"^[PTLVR]\.\s*", "sigla de falante dentro do texto"),
    (r"Entrada:\s*\w+;\s*Ofertas:", "créditos vazando para letra"),
]


def validar_texto_limpo(texto: str) -> str:
    if not isinstance(texto, str):
        return texto
    for padrao, descricao in ARTEFATOS:
        if re.search(padrao, texto):
            raise ValueError(f"Artefato '{descricao}' em: {texto[:80]!r}")
    return texto
