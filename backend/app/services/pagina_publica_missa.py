"""HTML público da missa que está liberada para visitantes.

A página é deliberadamente uma URL estável, não um arquivo por data. Assim, a
indexação pode descobrir a celebração disponível sem transformar o acervo em
conteúdo público permanente: passada a janela de acesso, esta página deixa de
exibir a edição anterior.
"""
from __future__ import annotations

from html import escape
from typing import Callable, Iterable
from urllib.parse import urlparse


MESES_PT_BR = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)


def _texto(valor: object | None) -> str:
    return escape(str(valor or "").strip())


def _url_fonte(valor: object | None) -> str:
    """Aceita somente URL absoluta HTTP(S) na referência externa."""
    url = str(valor or "").strip()
    partes = urlparse(url)
    if partes.scheme not in {"http", "https"} or not partes.netloc:
        return ""
    return escape(url, quote=True)


def selecionar_missa_publica(missas: Iterable[object], permitida: Callable[[object], bool]) -> object | None:
    """Retorna uma única edição, sempre delegando a decisão ao gate de acesso."""
    return next((missa for missa in missas if permitida(missa)), None)


def renderizar_pagina_missa(missa: object, blocos: Iterable[object], *, url: str) -> str:
    """Produz HTML rastreável sem confiar em conteúdo formatado vindo do banco."""
    data = getattr(missa, "data")
    data_iso = data.isoformat()
    data_legivel = f"{data.day} de {MESES_PT_BR[data.month - 1]} de {data.year}"
    celebracao = _texto(getattr(missa, "celebracao", None) or "Missa disponível")
    subtitulo = _texto(getattr(missa, "subtitulo", None))
    descricao = _texto(getattr(missa, "descricao", None))
    tempo = _texto(getattr(missa, "tempo_liturgico", None))
    fonte = _url_fonte(getattr(missa, "fonte_pdf_url", None))
    url_segura = _texto(url)

    partes: list[str] = []
    for bloco in blocos:
        if not getattr(bloco, "visivel", True):
            continue
        titulo = _texto(getattr(bloco, "titulo", None))
        referencia = _texto(getattr(bloco, "referencia", None))
        conteudo = _texto(getattr(bloco, "conteudo", None))
        if not any((titulo, referencia, conteudo)):
            continue
        cabecalho = ""
        if titulo:
            cabecalho += f"<h2>{titulo}</h2>"
        if referencia:
            cabecalho += f"<p class=\"referencia\">{referencia}</p>"
        corpo = f"<p>{conteudo}</p>" if conteudo else ""
        partes.append(f"<section>{cabecalho}{corpo}</section>")

    descricao_meta = descricao or f"{celebracao}. Folheto digital católico disponível no Dia de Missa."
    fonte_html = (
        f'<p class="fonte">Fonte de referência: <a href="{fonte}" rel="nofollow">folheto oficial da mesma edição</a>.</p>'
        if fonte else ""
    )
    subtitulo_html = f"<p class=\"subtitulo\">{subtitulo}</p>" if subtitulo else ""
    tempo_html = f"<p class=\"tempo\">{tempo}</p>" if tempo else ""
    descricao_html = f"<p class=\"descricao\">{descricao}</p>" if descricao else ""
    conteudo_html = "\n".join(partes) or "<p>A celebração está disponível no aplicativo.</p>"

    return f"""<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="index,follow,noarchive,max-snippet:-1">
    <link rel="canonical" href="{url_segura}">
    <title>{celebracao} — missa disponível | Dia de Missa</title>
    <meta name="description" content="{descricao_meta}">
    <script type="application/ld+json">{{"@context":"https://schema.org","@type":"Article","headline":"{celebracao}","datePublished":"{data_iso}","dateModified":"{data_iso}","inLanguage":"pt-BR","mainEntityOfPage":"{url_segura}","publisher":{{"@type":"Organization","name":"Dia de Missa","url":"https://diademissa.com.br/"}}}}</script>
  </head>
  <body>
    <main>
      <p>Folheto digital católico</p>
      <h1>{celebracao}</h1>
      <p><time datetime="{data_iso}">{data_legivel}</time></p>
      {subtitulo_html}
      {tempo_html}
      {descricao_html}
      <p>Conteúdo organizado a partir do folheto oficial da mesma edição e liberado enquanto esta celebração estiver disponível ao público.</p>
      {conteudo_html}
      {fonte_html}
      <p><a href="/">Abrir no Dia de Missa</a></p>
      <p>Após a celebração, esta edição passa a integrar o acervo para pessoas cadastradas.</p>
    </main>
  </body>
</html>"""
