"""Regra de elegibilidade do catálogo de locais de culto."""
from __future__ import annotations

from app.models.igreja import Igreja


def eh_local_catolico_oficial(igreja: Igreja) -> bool:
    """Aceita somente locais identificados pela Arquidiocese do Rio.

    O nome não é critério confiável de denominação — por exemplo, "São João
    Batista" pode ser uma paróquia católica. O identificador de origem da
    Arquidiocese é a evidência canônica usada pelo catálogo.
    """
    return igreja.arqrio_local_id is not None
