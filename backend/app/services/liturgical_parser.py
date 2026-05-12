from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional

from app.services.pdf_parser import LinhaTexto


@dataclass
class BlocoExtraido:
    titulo: str
    linhas_raw: list[str] = field(default_factory=list)
    linhas_formatadas: list[str] = field(default_factory=list)
    pagina_inicio: int = 0

    @property
    def conteudo(self) -> str:
        return self._montar_conteudo(self.linhas_raw)

    @property
    def conteudo_formatado(self) -> str:
        if self.linhas_formatadas:
            return self._montar_conteudo(self.linhas_formatadas)
        return self.conteudo

    def _montar_conteudo(self, lines: list[str]) -> str:
        if not lines:
            return ""

        paragrafos: list[str] = []
        paragrafo_atual: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if paragrafo_atual:
                    paragrafos.append(" ".join(paragrafo_atual))
                    paragrafo_atual = []
                continue

            if stripped in ("*P.*", "*T.*", "*L.*"):
                if paragrafo_atual:
                    paragrafos.append(" ".join(paragrafo_atual))
                    paragrafo_atual = []
                paragrafos.append(stripped)
                continue

            if stripped.startswith("## ") or stripped.startswith("**") or stripped.startswith("*"):
                if paragrafo_atual:
                    paragrafos.append(" ".join(paragrafo_atual))
                    paragrafo_atual = []
                paragrafos.append(stripped)
                continue

            if stripped.startswith("(") and stripped.endswith(")"):
                if paragrafo_atual:
                    paragrafos.append(" ".join(paragrafo_atual))
                    paragrafo_atual = []
                paragrafos.append(stripped)
                continue

            paragrafo_atual.append(stripped)

        if paragrafo_atual:
            paragrafos.append(" ".join(paragrafo_atual))

        return "\n\n".join(paragrafos)

    def add_line(self, line: str):
        self.linhas_raw.append(line)

    def add_linha_formatada(self, line: str):
        self.linhas_formatadas.append(line)


SECOES_LITURGICAS = [
    "Ritos Iniciais", "Liturgia da Palavra",
    "Liturgia Eucarística", "Liturgia Eucaristica",
    "Ritos Finais",
]

TIPOS_HINO = {"canto_entrada", "salmo_responsorial", "ofertorio", "comunhao", "canto_final", "gloria"}


def _limpar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


def _eh_num_bloco(linha: str) -> bool:
    return bool(re.match(r"^\s*\d+\.\s*$", linha))


def _extrair_num(linha: str) -> Optional[int]:
    m = re.match(r"^\s*(\d+)\.\s*$", linha)
    return int(m.group(1)) if m else None


def _prox_linha(linhas: list[LinhaTexto], idx: int, max_look=3) -> str:
    for j in range(idx + 1, min(idx + max_look + 1, len(linhas))):
        t = linhas[j].texto.strip()
        if t and not _eh_num_bloco(linhas[j].texto):
            return t
    return ""


def segmentar_blocos(linhas: list[LinhaTexto]) -> list[BlocoExtraido]:
    blocos: list[BlocoExtraido] = []
    bloco_atual: Optional[BlocoExtraido] = None

    ultimo_tipo_classificado = ""
    dentro_de_hino = False
    linhas_desde_ultimo_bloco = 999

    textos = []
    for i, l in enumerate(linhas):
        textos.append((i, l.texto.rstrip(), l.texto_formatado.rstrip(), l.pagina))

    i = 0
    while i < len(textos):
        idx, texto_raw, texto_fmt_raw, pagina = textos[i]
        texto = texto_raw.strip()
        texto_fmt = texto_fmt_raw.strip()
        i += 1

        if not texto:
            continue

        # Remove header garbage
        if "AAnnoo" in texto or "A –" in texto and "no" in texto:
            continue
        if "www.arqrio" in texto.lower() or "arqrio" in texto.lower():
            continue
        if "EDITORA NOSSA SENHORA" in texto.upper():
            continue
        if "Rua Benjamin Constant" in texto:
            continue
        if "Publicação da Comissão" in texto or "Publicação da Comissão" in texto:
            continue
        if "COM APROVAÇÃO ECLESIÁSTICA" in texto.upper() or "COM APROVACAO ECLESIASTICA" in texto.upper():
            continue
        if "Cantos selecionados" in texto:
            continue
        if texto.startswith("Portal da Arquidiocese") or texto.startswith("PORTAL DA ARQUIDIOCESE"):
            continue
        if texto.startswith("Do Rio de Janeiro") or texto.startswith("DO RIO DE JANEIRO"):
            continue
        if texto.startswith("Ano Jubilar"):
            continue
        if texto.startswith("Produção:") or texto.startswith("Vicariato"):
            continue
        if texto.startswith("Folheto Oficial"):
            continue
        if texto == "Versão Celular" or texto == "-":
            continue
        if texto.startswith("LEITURAS DA SEMANA") or texto.startswith("Leituras da Semana"):
            continue

        # Section header
        if texto in SECOES_LITURGICAS:
            if bloco_atual and (bloco_atual.linhas_raw or bloco_atual.titulo):
                blocos.append(bloco_atual)
            bloco_atual = BlocoExtraido(titulo=texto, pagina_inicio=pagina)
            dentro_de_hino = False
            linhas_desde_ultimo_bloco = 0
            continue

        # Numbered block start
        if _eh_num_bloco(texto):
            n = _extrair_num(texto)
            prox = _prox_linha(linhas, idx)

            if not prox:
                if bloco_atual:
                    bloco_atual.add_line(f"[{texto}]")
                continue

            prox_clean = _limpar(prox)
            prox_upper = prox_clean.upper()

            # Stanza detection: if next line starts with "/" or "luia", it's a stanza
            if prox_clean.startswith("/") or prox_clean.startswith("luia") or prox_clean.startswith("Aleluia"):
                if bloco_atual:
                    bloco_atual.add_line("")
                    bloco_atual.add_line(prox_clean)
                continue

            # Se está dentro de hino, número baixo E próximo texto não parece título
            parece_titulo = any(p in prox_upper for p in [
                "CANTO", "ANTÍFONA", "ANTIFONA", "SAUDAÇÃO", "SAUDACAO",
                "ATO", "GLÓRIA", "GLORIA", "HINO", "COLETA", "ORAÇÃO", "ORACAO",
                "LEITURA", "SALMO", "SEQUÊNCIA", "SEQUENCIA", "ACLAMAÇÃO", "ACLAMACAO",
                "EVANGELHO", "HOMILIA", "PROFISSÃO", "PROFISSAO", "CREIO",
                "PRECES", "OFERTÓRIO", "OFERTORIO", "OFERTAS",
                "CONVITE", "ORAI", "SANTO", "CORDEIRO",
                "RITO", "PAI NOSSO", "VIVÊNCIA", "VIVENCIA",
                "BÊNÇÃO", "BENCAO", "DESPEDIDA",
            ])

            if not parece_titulo:
                if bloco_atual:
                    bloco_atual.add_line("")
                    bloco_atual.add_line(prox_clean)
                continue

            if bloco_atual and (bloco_atual.linhas_raw or bloco_atual.titulo):
                blocos.append(bloco_atual)

            bloco_atual = BlocoExtraido(titulo=prox_clean, pagina_inicio=pagina)
            linhas_desde_ultimo_bloco = 0

            # Detectar se é hino (tem sub-numeros)
            if any(p in prox_clean.lower() for p in ["canto", "salmo", "comunhão", "comunhao", "hino", "glória", "gloria", "oferta"]):
                dentro_de_hino = True
            else:
                dentro_de_hino = False
            continue

        linhas_desde_ultimo_bloco += 1

        # Handle Bible reference lines as content markers
        if re.match(r"^[A-Z][a-záéíóúçãõê]+\s+\d+[,:]", texto):
            if not bloco_atual:
                bloco_atual = BlocoExtraido(titulo="", pagina_inicio=pagina)
            bloco_atual.add_line(f"**{texto}**")
            continue

        # Handle liturgical markers
        if texto in ("P.", "T.", "L."):
            if not bloco_atual:
                bloco_atual = BlocoExtraido(titulo="", pagina_inicio=pagina)
            bloco_atual.add_line(f"*{texto}*")
            continue

        # Handle standalone "Ant" (Antífona abbreviation)
        if texto == "Ant":
            if bloco_atual:
                bloco_atual.add_line("**Antífona:**")
            continue

        # Handle REFRÃO
        if texto.startswith("REFRÃO") or texto.startswith("REFRÃƒO"):
            if not bloco_atual:
                bloco_atual = BlocoExtraido(titulo="", pagina_inicio=pagina)
            bloco_atual.add_line(f"## {texto}")
            continue

        if not bloco_atual:
            bloco_atual = BlocoExtraido(titulo="", pagina_inicio=pagina)

        # Join hyphenated words
        if bloco_atual.linhas_raw and bloco_atual.linhas_raw[-1].endswith("-"):
            bloco_atual.linhas_raw[-1] = bloco_atual.linhas_raw[-1][:-1] + texto
        else:
            bloco_atual.add_line(texto)

    if bloco_atual and (bloco_atual.linhas_raw or bloco_atual.titulo):
        blocos.append(bloco_atual)

    # Remove empty section headers
    blocos = [b for b in blocos if not (b.titulo in SECOES_LITURGICAS and not b.linhas_raw and not b.conteudo)]

    # Remove first block if it's clearly intro/meta
    if blocos and blocos[0].titulo not in SECOES_LITURGICAS:
        primeiro = (blocos[0].titulo + " " + blocos[0].conteudo)[:200].lower()
        if any(p in primeiro for p in ["versão", "folheto", "ano a", "ano jubilar", "editora", "ascensão do senhor", "solenidade"]):
            blocos.pop(0)

    # Merge only true fragment blocks
    merged: list[BlocoExtraido] = []

    for b in blocos:
        if not merged:
            merged.append(b)
            continue

        prev = merged[-1]

        if b.titulo in SECOES_LITURGICAS and not b.linhas_raw and not b.conteudo:
            continue

        should_merge = False

        if b.titulo:
            t = b.titulo.strip()
            if t.startswith("/") or t.startswith("luia") or t.startswith("Aleluia"):
                should_merge = True
            elif t[0].islower():
                should_merge = True
            elif len(t) < 3:
                should_merge = True
            # Merge if prev block is song/hymn and current title is not a known liturgical section
            elif prev.titulo.lower() in SECOES_LITURGICAS:
                pass
            else:
                prev_lower = prev.titulo.lower()
                prev_is_hymn = any(p in prev_lower for p in ["canto de", "canto das", "canto da", "salmo", "comunhão", "hino de", "rito da comunhão"])
                cur_is_known = any(p in t.upper() for p in [
                    "PRIMEIRA LEITURA", "SEGUNDA LEITURA", "EVANGELHO", "HOMILIA",
                    "PROFISSÃO", "ORAÇÃO DOS", "ACLAMAÇÃO",
                    "BÊNÇÃO", "RITO DA", "VIVÊNCIA", "PAI NOSSO", "CORDEIRO",
                    "COLETA", "ATO PENITENCIAL", "SAUDAÇÃO", "GLÓRIA", "GLORIA",
                    "CONVITE", "OFERTÓRIO", "OFERTAS", "SOBRE AS", "LITURGIA",
                ])
                if prev_is_hymn and not cur_is_known:
                    should_merge = True

        if not b.titulo or len(b.titulo.strip()) < 2:
            should_merge = True

        if should_merge:
            prev.linhas_raw.append("")
            prev.linhas_raw.append(b.titulo or "")
            prev.linhas_raw.extend(b.linhas_raw)
        else:
            merged.append(b)

    return merged


def extrair_referencia(texto: str) -> Optional[str]:
    m = re.search(r"([A-Z][a-záéíóúçãõê]+\s+\d+[,.:]\d+(?:[,-]\d+)?)", texto)
    return m.group(1).strip() if m else None
