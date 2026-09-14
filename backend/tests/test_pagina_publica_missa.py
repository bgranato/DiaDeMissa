from datetime import date
from types import SimpleNamespace

from app.services.pagina_publica_missa import renderizar_pagina_missa, selecionar_missa_publica


def test_pagina_publica_escapa_texto_e_mostra_apenas_blocos_visiveis():
    missa = SimpleNamespace(
        data=date(2026, 9, 20),
        celebracao="25º Domingo <comum>",
        subtitulo=None,
        descricao="Celebração <especial>",
        tempo_liturgico="Tempo Comum",
        fonte_pdf_url="https://fonte.example/folheto.pdf",
    )
    blocos = [
        SimpleNamespace(visivel=True, titulo="Evangelho", referencia="Lc 1, 1", conteudo="<script>alert(1)</script>"),
        SimpleNamespace(visivel=False, titulo="Interno", referencia=None, conteudo="não publicar"),
    ]

    html = renderizar_pagina_missa(missa, blocos, url="https://diademissa.com.br/missa-disponivel")

    assert "25º Domingo &lt;comum&gt;" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "não publicar" not in html
    assert 'rel="nofollow"' in html
    assert 'datetime="2026-09-20"' in html
    assert "20 de setembro de 2026" in html


def test_pagina_publica_nao_coloca_url_insegura_como_link():
    missa = SimpleNamespace(
        data=date(2026, 9, 20), celebracao="Missa", subtitulo=None,
        descricao=None, tempo_liturgico=None, fonte_pdf_url="javascript:alert(1)",
    )

    html = renderizar_pagina_missa(missa, [], url="https://diademissa.com.br/missa-disponivel")

    assert "javascript:alert" not in html


def test_pagina_publica_nao_ignora_o_gate_de_acesso_do_acervo():
    passada = SimpleNamespace(data=date(2026, 9, 13))
    liberada = SimpleNamespace(data=date(2026, 9, 20))

    missa = selecionar_missa_publica([passada, liberada], lambda item: item is liberada)

    assert missa is liberada
    assert selecionar_missa_publica([passada], lambda _: False) is None
