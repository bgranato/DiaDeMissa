import datetime
from pathlib import Path
from typing import Union

from app.pipeline.extract import extrair_texto_estruturado
from app.pipeline.clean import limpar
from app.pipeline.download import obter_pdf
from app.schema.missa import Missa


def processar_pdf(fonte: Union[str, Path, None] = None) -> Missa:
    if fonte is None:
        conteudo = obter_pdf()
        texto_bruto = extrair_texto_estruturado(conteudo)
    else:
        pdf_path = Path(fonte) if isinstance(fonte, str) else fonte
        texto_bruto = extrair_texto_estruturado(pdf_path)

    texto_limpo = limpar(texto_bruto)

    from app.pipeline.structure import estruturar
    return estruturar(texto_limpo)
