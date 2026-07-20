from __future__ import annotations

import re
import unicodedata


def limpar(texto: str) -> str:
    texto = unicodedata.normalize("NFC", texto)
    # De-hifenização de quebra de linha ("necessá-\nrio" -> "necessário"), MAS só
    # quando o caractere antes do "-" é LETRA. Se for dígito, o "-" é hífen de
    # intervalo de citação bíblica ("Ct 3,1-\n4a") e NÃO pode ser removido —
    # senão vira referência errada ("Ct 3,14a").
    texto = re.sub(r"(\w*[^\W\d])-\s*\n\s*(\w+)", r"\1\2", texto)
    # Intervalo numérico quebrado na linha ("3,1-\n4a"): remove só a quebra,
    # PRESERVANDO o hífen do intervalo -> "3,1-4a".
    texto = re.sub(r"(\d-)\s*\n\s*(\d)", r"\1\2", texto)
    texto = re.sub(
        r"([a-záéíóúâêôãõçà,;:])\s*\n\s*([a-záéíóúâêôãõçà])",
        r"\1 \2",
        texto,
    )
    texto = re.sub(r"(\s|^)([PTLVR])\.([A-ZÁÉÍÓÚÂÊÔÃÕÇ])", r"\1\2. \3", texto)
    # Indicadores ordinais: o folheto PDF mostra "10º Domingo" mas pdfplumber/poppler
    # extrai como "10o Domingo" (letra 'o' minúscula). Recompõe: dígitos seguidos
    # de 'o' (ou 'a' p/ feminino: "1a Carta") quando não é parte de uma palavra.
    # Aceita: "10o", "1a", "2º" (já correto, mantém), "3ª" — sempre antes de fim
    # de palavra ou espaço/pontuação.
    # Lookbehind (?<![\d.,-]) impede que a citação bíblica seja corrompida:
    # "Ex 19,2-6a" ou "Jo 15,26b.27a" NÃO viram ordinal (6ª/27ª) — o dígito vem
    # colado a vírgula/hífen/ponto. Ordinais soltos ("10o Domingo", "1a Carta"),
    # precedidos de espaço/início, continuam sendo convertidos.
    texto = re.sub(r"(?<![\d.,\-])(\d+)o(?=\W|$)", r"\1º", texto)
    texto = re.sub(r"(?<![\d.,\-])(\d+)a(?=\W|$)", r"\1ª", texto)
    # A extração às vezes mis-codifica a LETRA do versículo como ordinal
    # ("Jo 15,26b.27ª" no lugar de "27a"). Reverte SÓ dígito+ª/º seguido de
    # pontuação/fim — não toca ordinais reais ("1ª Leitura", "10º Domingo",
    # "2ª-FEIRA"), que vêm seguidos de espaço ou hífen.
    texto = re.sub(r"(\d)ª(?=[).,;:]|$)", r"\1a", texto)
    texto = re.sub(r"(\d)º(?=[).,;:]|$)", r"\1o", texto)
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    texto = "\n".join(linha.strip() for linha in texto.split("\n"))
    return texto.strip()
