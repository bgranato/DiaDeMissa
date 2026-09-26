"""Blindagem fina do auditor vs folheto-fonte (SEM LLM).

As checagens em `_checar_fonte_fino` cobrem a fidelidade que antes dependia do
conferente multimodal: falas P/T/L (palavras + resposta curta literal), refrão,
referência bíblica e título-número. Todas SEV_ALTA e determinísticas.
"""
import types

from app.services import auditor_missa as A


FONTE = (
    "20. Oração Eucarística III\n"
    "T. Amém.\n"
    "P. O Senhor esteja convosco.\n"
    "T. Ele está no meio de nós.\n"
    "REFRÃO: Dai-lhes, Senhor, o pão da vida.\n"
    "Prefácio das Missas de Santa Maria — Ez 18,25-28\n"
    "Deus de infinita misericórdia.\n"
    "Acolhei, Senhor, as nossas oferendas.\n"
)


def _missa(ce_lista):
    blocos = []
    for i, ce in enumerate(ce_lista, start=1):
        blocos.append(types.SimpleNamespace(
            tipo=ce.get("tipo", "texto"),
            titulo=ce.get("titulo", f"Bloco {i}"),
            ordem=i,
            conteudo_estruturado=ce,
        ))
    return types.SimpleNamespace(blocos=blocos)


def _achados(missa, regra=None):
    achados = []
    src_norm = A._norm(FONTE)
    A._checar_fonte_fino(missa, src_norm, achados)
    if regra:
        return [a for a in achados if a.regra == regra]
    return achados


def test_turno_curto_reordenado_e_flagrado():
    # "Ele está no meio de nós." reordenado (mesmas palavras) NÃO passa no literal.
    missa = _missa([{
        "turnos": [{"falante": "T", "texto": "No meio de nós, ele está."}],
    }])
    achados = _achados(missa, "fala_curta_fora_do_folheto")
    assert len(achados) == 1, f"esperava 1 achado, veio: {achados}"
    assert achados[0].severidade == A.SEV_ALTA


def test_turno_fiel_nao_gera_achado():
    missa = _missa([{
        "turnos": [
            {"falante": "P", "texto": "O Senhor esteja convosco."},
            {"falante": "T", "texto": "Ele está no meio de nós."},
        ],
    }])
    assert _achados(missa) == []


def test_turno_com_palavra_fora_do_folheto_e_flagrado():
    # "convosquíssimo" (palavra inventada) → fala_fora_do_folheto.
    missa = _missa([{
        "turnos": [{"falante": "P", "texto": "O Senhor convosquíssimo esteja."}],
    }])
    achados = _achados(missa, "fala_fora_do_folheto")
    assert len(achados) == 1, f"esperava 1 achado, veio: {achados}"


def test_refrao_fora_do_folheto_e_flagrado():
    missa = _missa([{
        "refrao": ["Dai-lhes, Senhor, a vida eterna."],  # "eterna" não está no fonte
    }])
    achados = _achados(missa, "refrao_fora_do_folheto")
    assert len(achados) == 1, f"esperava 1 achado, veio: {achados}"


def test_refrao_fiel_nao_gera_achado():
    missa = _missa([{
        "refrao": ["Dai-lhes, Senhor, o pão da vida."],
    }])
    assert _achados(missa) == []


def test_referencia_fora_do_folheto_e_flagrada():
    missa = _missa([{
        "referencia": "Cf. Dn 99,1-2",  # não consta no fonte
    }])
    achados = _achados(missa, "referencia_fora_do_folheto")
    assert len(achados) == 1, f"esperava 1 achado, veio: {achados}"


def test_referencia_fiel_nao_gera_achado():
    missa = _missa([{
        "referencia": "Ez 18,25-28",
    }])
    assert _achados(missa) == []


def test_referencia_ocr_l_em_vez_de_1_nao_gera_achado():
    """Caso real 08/08: o extrator do PDF lê '10' como 'l0' (L minúsculo) na
    referência do Salmo. A tolerância 'l'→'1' não pode acusar."""
    fonte_ocr = (
        "7. Salmo Responsorial [Sl 84(85),9ab-l0.11-12.13-14 (R. 8)]\n"
        "REFRÃO: Mostrai-nos, ó Senhor, vossa bondade.\n"
    )
    missa = _missa([{
        "tipo": "salmo",
        "titulo": "Salmo Responsorial",
        "referencia": "Sl 84(85),9ab-10.11-12.13-14 (R. 8)",
    }])
    achados = []
    A._checar_referencia_no_fonte(missa, A._norm(fonte_ocr), achados)
    assert achados == [], f"deveria tolerar o artefato 'l0', veio: {achados}"


def test_titulo_numerado_fora_do_folheto_e_flagrado():
    missa = _missa([{
        "numero_folheto": 20,
        "titulo": "Oração Eucarística IV",  # o fonte tem "III"
    }])
    achados = _achados(missa, "titulo_fora_do_folheto")
    assert len(achados) == 1, f"esperava 1 achado, veio: {achados}"


def test_titulo_fiel_nao_gera_achado():
    missa = _missa([{
        "numero_folheto": 20,
        "titulo": "Oração Eucarística III",
    }])
    assert _achados(missa) == []