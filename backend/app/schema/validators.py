from __future__ import annotations
import re
from typing import Annotated

# Padrões proibidos em qualquer campo de texto.
# Nota: a barra ` / ` é separador legítimo de verso (Hino de Louvor, Glória etc),
# então NÃO é mais tratada como artefato. Só barras no início/fim do texto são
# bloqueadas porque são artefatos reais de extração.
ARTEFATOS = [
    (r"^/|/$", "barra no início/fim"),
    (r"##|^\*\*|\*\*$", "markdown vazado"),
    (r"\w+-\s*\n", "hifenização de quebra de linha"),
    (r"[a-záéíóúâêôãõç][A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]", "palavras coladas (camelCase)"),
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
