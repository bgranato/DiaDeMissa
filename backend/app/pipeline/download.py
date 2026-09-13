from __future__ import annotations

import hashlib
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

import httpx

# A URL fixa abaixo é mantida apenas por compatibilidade com instalações antigas.
# A montagem produtiva não a usa: a página oficial de folhetos informa qual é a
# edição "Celular" e qual é a "Celebrante" de cada data.
PDF_URL = "https://www.arqrio.com.br/app/painel/amissa/amissa.pdf"
FOLHETOS_URL = "https://arqrio.org.br/folhetos"
# Cache de PDFs em path absoluto fora do diretório do app (writable, persistente,
# imune a deploy rsync --delete e a problemas transitórios de filesystem do app).
# Override via env DIADEMISSA_PDF_CACHE; em dev, default é ./data/pdfs (relativo).
_DEFAULT_CACHE = "/var/lib/diademissa/pdfs" if Path("/var/lib/diademissa").exists() else "data/pdfs"
CACHE_DIR = Path(os.environ.get("DIADEMISSA_PDF_CACHE", _DEFAULT_CACHE))
TIMEOUT = 30
# A página oficial protege requisições sem identificação de navegador. A
# identificação é estável, transparente e só é usada para leitura dos próprios
# links públicos da Arquidiocese; não tenta burlar login ou qualquer restrição.
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DiaDeMissa/1.0; +https://diademissa.com.br)",
    "Accept-Language": "pt-BR,pt;q=0.9",
}


class FonteFolhetoIndisponivel(RuntimeError):
    """A edição oficial exigida pelo contrato não estava disponível."""


@dataclass(frozen=True)
class FonteFolheto:
    """Um link oficial, classificado pela própria página da Arquidiocese."""

    data: date
    tipo: str  # celular | celebrante
    url: str
    titulo: str


def _normalizar(valor: str) -> str:
    sem_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", valor or "")
        if not unicodedata.combining(c)
    )
    return re.sub(r"\s+", " ", sem_acentos.lower()).strip()


def _tipo_folheto(valor: str) -> str | None:
    normalizado = _normalizar(valor)
    if "celular" in normalizado:
        return "celular"
    if "celebrante" in normalizado:
        return "celebrante"
    if "assembleia" in normalizado:
        return "assembleia"
    return None


def _data_do_link(valor: str) -> date | None:
    encontrado = re.search(r"(\d{2})-(\d{2})-(\d{4})", valor or "")
    if not encontrado:
        encontrado = re.search(r"(\d{2})/(\d{2})/(\d{4})", valor or "")
    if not encontrado:
        return None
    try:
        dia, mes, ano = (int(x) for x in encontrado.groups())
        return date(ano, mes, dia)
    except ValueError:
        return None


class _LeitorFolhetos(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        dados = {chave.lower(): valor or "" for chave, valor in attrs}
        href = dados.get("href", "")
        identificador = dados.get("data-folheto-id", "")
        titulo = dados.get("data-folheto-titulo", "")
        if href and (identificador or titulo):
            self.links.append((href, identificador, titulo))


def resolver_fontes_oficiais(data_edicao: date, *, html: str | None = None) -> tuple[FonteFolheto, FonteFolheto]:
    """Resolve **somente** Celular e Celebrante na página oficial.

    Assembleia é deliberadamente lida apenas para ser descartada: não há fallback
    para ela, pois suas colunas compactas não são uma referência segura para a
    extração. A falta de qualquer uma das duas fontes exigidas fecha o gate.
    """
    if html is None:
        with httpx.Client(timeout=httpx.Timeout(TIMEOUT), follow_redirects=True, headers=HTTP_HEADERS) as client:
            resposta = client.get(FOLHETOS_URL)
            resposta.raise_for_status()
            html = resposta.text

    leitor = _LeitorFolhetos()
    leitor.feed(html)
    encontradas: dict[str, FonteFolheto] = {}
    for href, identificador, titulo in leitor.links:
        if _data_do_link(identificador) != data_edicao and _data_do_link(titulo) != data_edicao:
            continue
        tipo = _tipo_folheto(f"{identificador} {titulo}")
        if tipo == "assembleia":
            continue
        if tipo in ("celular", "celebrante") and tipo not in encontradas:
            encontradas[tipo] = FonteFolheto(
                data=data_edicao,
                tipo=tipo,
                url=urljoin(FOLHETOS_URL, href),
                titulo=titulo or identificador,
            )

    faltantes = [tipo for tipo in ("celular", "celebrante") if tipo not in encontradas]
    if faltantes:
        raise FonteFolhetoIndisponivel(
            f"folheto oficial indisponível para {data_edicao.isoformat()}: {', '.join(faltantes)}"
        )
    return encontradas["celular"], encontradas["celebrante"]


def baixar_fontes_oficiais(data_edicao: date) -> tuple[FonteFolheto, bytes, FonteFolheto, bytes]:
    """Baixa as duas referências do contrato em uma mesma execução.

    A ordem do retorno é intencional e auditável: Celular (construtor) primeiro,
    Celebrante (crítico secundário) depois.
    """
    celular, celebrante = resolver_fontes_oficiais(data_edicao)
    with httpx.Client(timeout=httpx.Timeout(TIMEOUT), follow_redirects=True, headers=HTTP_HEADERS) as client:
        resposta_celular = client.get(celular.url)
        resposta_celular.raise_for_status()
        resposta_celebrante = client.get(celebrante.url)
        resposta_celebrante.raise_for_status()
    _validar_pdf(resposta_celular.content, "Celular")
    _validar_pdf(resposta_celebrante.content, "Celebrante")
    return celular, resposta_celular.content, celebrante, resposta_celebrante.content


def _validar_pdf(conteudo: bytes, tipo: str) -> None:
    """Recusa página HTML/erro no lugar do PDF oficial.

    A Arquidiocese prefixa alguns PDFs com poucos espaços de saída do PHP; por
    isso a assinatura pode aparecer após o byte zero, mas obrigatoriamente nos
    primeiros 1.024 bytes previstos pela especificação do formato.
    """
    if conteudo.find(b"%PDF-") < 0 or conteudo.find(b"%PDF-") >= 1024:
        raise FonteFolhetoIndisponivel(f"fonte {tipo} não retornou um PDF válido")


def obter_pdf() -> bytes:
    """Compatibilidade: retorna a referência Celular, nunca Assembleia.

    A rota produtiva usa :func:`baixar_fontes_oficiais` para preservar também a
    versão Celebrante e executar a conferência secundária obrigatória.
    """
    _celular, conteudo, _celebrante, _conteudo_celebrante = baixar_fontes_oficiais(date.today())
    return conteudo


def hash_pdf(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()
