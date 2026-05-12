from pathlib import Path
from typing import Union

from app.pipeline.extract import extrair_texto_estruturado
from app.pipeline.clean import limpar
from app.schema.missa import Missa


def processar_pdf(fonte: Union[str, Path]) -> Missa:
    pdf_path = Path(fonte) if isinstance(fonte, str) else fonte
    texto_bruto = extrair_texto_estruturado(pdf_path)
    texto_limpo = limpar(texto_bruto)

    from app.pipeline.structure import estruturar
    return estruturar(texto_limpo)
