"""Blindagem da Oração dos Fiéis no auditor.

A resposta (refrão) das Preces TEM de existir no folheto-fonte. Se a resposta
renderizada não consta na fonte (ex.: refrão genérico do Missal injetado por
cima do refrão real do folheto), o auditor deve reprovar com CRÍTICA
'resposta_preces_fora_do_folheto'.
"""
import types

from app.services import auditor_missa as A


# Fonte com o refrão REAL do folheto e SEM a palavra "escutai".
FONTE = (
    "13. Oração dos Fiéis\n"
    "Nesta solenidade dos Apóstolos São Pedro e São Paulo, apresentemos ao Pai "
    "as súplicas, dizendo:\n"
    "Senhor, fortalecei a vossa Igreja na fé dos Apóstolos.\n"
    "1. Pela Santa Igreja de Deus, rezemos.\n"
    "2. Pelo Papa Leão e pelos bispos, rezemos.\n"
)


def _missa_com_resposta(resposta: str):
    """Stub de missa com um bloco Oração dos Fiéis cujo turno T = `resposta`."""
    bloco = types.SimpleNamespace(
        tipo="dialogo",
        titulo="Oração dos Fiéis",
        ordem=13,
        conteudo_estruturado={
            "turnos": [
                {"falante": "P", "texto": "Apresentemos ao Pai as súplicas, dizendo:"},
                {"falante": "T", "texto": resposta},
                {"falante": "L", "texto": "Pela Santa Igreja de Deus, rezemos."},
                {"falante": "T", "texto": resposta},
                {"falante": "L", "texto": "Pelo Papa Leão e pelos bispos, rezemos."},
                {"falante": "T", "texto": resposta},
            ]
        },
    )
    return types.SimpleNamespace(blocos=[bloco])


def _achados_preces(resposta: str):
    achados = []
    src_norm = A._norm(FONTE)
    A._checar_resposta_preces_no_fonte(_missa_com_resposta(resposta), src_norm, achados)
    return [a for a in achados if a.regra == "resposta_preces_fora_do_folheto"]


def test_refrao_real_do_folheto_nao_gera_achado():
    # Refrão que EXISTE no folheto-fonte → nenhum achado.
    achados = _achados_preces("Senhor, fortalecei a vossa Igreja na fé dos Apóstolos.")
    assert achados == [], f"não deveria gerar achado, veio: {achados}"


def test_refrao_generico_gera_critica():
    # Refrão genérico do Missal ("escutai"), ausente do folheto → CRÍTICA.
    achados = _achados_preces("Senhor, escutai a nossa prece.")
    assert len(achados) == 1, f"esperava 1 achado, veio: {achados}"
    assert achados[0].severidade == A.SEV_CRITICA
    assert achados[0].regra == "resposta_preces_fora_do_folheto"
