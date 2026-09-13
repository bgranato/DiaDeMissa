from datetime import date

import pytest

from app.pipeline.download import FonteFolhetoIndisponivel, _validar_pdf, resolver_fontes_oficiais


HTML_FOLHETOS = """
<a href="/assembleia.pdf" data-folheto-id="13-09-2026-assembleia"
   data-folheto-titulo="13/09/2026 (Assembléia)">Assembleia</a>
<a href="/celular.pdf" data-folheto-id="13-09-2026-celular"
   data-folheto-titulo="13/09/2026 (Celular)">Celular</a>
<a href="/celebrante.pdf" data-folheto-id="13-09-2026-celebrante"
   data-folheto-titulo="13/09/2026 (Celebrante)">Celebrante</a>
"""


def test_resolve_celular_como_principal_e_celebrante_como_secundario():
    celular, celebrante = resolver_fontes_oficiais(date(2026, 9, 13), html=HTML_FOLHETOS)

    assert celular.tipo == "celular"
    assert celular.url == "https://arqrio.org.br/celular.pdf"
    assert celebrante.tipo == "celebrante"
    assert celebrante.url == "https://arqrio.org.br/celebrante.pdf"
    assert "assembleia" not in {celular.tipo, celebrante.tipo}


def test_nunca_faz_fallback_para_assembleia():
    apenas_assembleia = HTML_FOLHETOS.split("<a href=\"/celular.pdf\"")[0]

    with pytest.raises(FonteFolhetoIndisponivel, match="celular, celebrante"):
        resolver_fontes_oficiais(date(2026, 9, 13), html=apenas_assembleia)


def test_aceita_assinatura_pdf_com_prefixo_do_servidor_e_recusa_html():
    _validar_pdf(b"    \r\n%PDF-1.5 conteudo", "Celular")

    with pytest.raises(FonteFolhetoIndisponivel, match="não retornou um PDF"):
        _validar_pdf(b"<html>erro</html>", "Celular")
