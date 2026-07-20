"""Teste de regressão — folheto 2026-07-19 (16º Domingo do Tempo Comum).

Fixa os erros de parsing/estruturação encontrados em auditoria manual do folheto
contra a montagem do app. Roda o pipeline REAL (multimodal) sobre o PDF-fixture e
verifica:
  (a) "e paz na terra" é turno T, sem o marcador "T." colado no texto (fix clean.py);
  (b) referência do Evangelho "Mt 13,24-43 (mais breve 13,24-30)" e colchetes da
      forma breve preservados no corpo dos versículos;
  (c) 4 intenções numeradas na Oração dos Fiéis;
  (d) repetições "Tantas graças..." presentes no Canto Final;
  (e) rubrica "Momento de silêncio para oração pessoal" 1x, no bloco da Comunhão.

Como as asserções (b)-(e) dependem do LLM lendo o PDF, o teste PULA quando não há
ANTHROPIC_API_KEY (ex.: CI sem segredo). Onde a chave existe, ele exercita o
pipeline multimodal ponta a ponta.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PDF = FIXTURES_DIR / "folheto_2026-07-19.pdf"

pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY") or not PDF.exists(),
    reason="requer ANTHROPIC_API_KEY e o PDF-fixture (pipeline multimodal real)",
)


@pytest.fixture(scope="module")
def missa():
    # Força o caminho multimodal (o que roda em produção) para este teste.
    os.environ["USAR_LLM"] = "1"
    os.environ["USAR_LLM_MULTIMODAL"] = "1"
    from app.pipeline import processar_pdf
    return processar_pdf(PDF)


# --------------------------- helpers ---------------------------

def _blocos(missa):
    return list(missa.blocos or [])


def _por_titulo(missa, *chaves):
    chaves = [c.lower() for c in chaves]
    for b in _blocos(missa):
        t = (getattr(b, "titulo", "") or "").lower()
        if any(c in t for c in chaves):
            yield b


def _turnos(b):
    return list(getattr(b, "turnos", None) or [])


def _versos_estrofes(b):
    out = []
    for e in getattr(b, "estrofes", None) or []:
        if isinstance(e, str):
            out.append(e)
        elif isinstance(e, (list, tuple)):
            out.extend(str(x) for x in e)
        elif isinstance(e, dict):
            out.append(str(e.get("texto") or ""))
    return out


# --------------------------- (a) marcador T. colado ---------------------------

def test_a_paz_na_terra_turno_T_sem_marcador_colado(missa):
    hino = next(_por_titulo(missa, "hino de louvor", "glória", "gloria"), None)
    assert hino is not None, "bloco do Hino de Louvor/Glória não encontrado"
    turnos = _turnos(hino)
    assert turnos, "Hino sem turnos (esperado diálogo P/T)"
    # existe um turno T cujo texto começa com "e paz na terra" (sem "T." colado)
    alvo = [t for t in turnos if str(getattr(t, "texto", "") or "").lower().startswith("e paz na terra")]
    assert alvo, f"turno 'e paz na terra' não encontrado; turnos={[getattr(t,'texto','')[:20] for t in turnos]}"
    assert str(getattr(alvo[0], "falante", "")) == "T", "o verso 'e paz na terra' deve ser falante T"
    # nenhum turno pode ter o marcador colado ("T.e", "P.Em"...) no início do texto
    for t in turnos:
        txt = str(getattr(t, "texto", "") or "")
        assert not re.match(r"^[PTLVR]\.\S", txt), f"marcador colado no texto: {txt[:20]!r}"


# --------------------------- (b) Evangelho: ref + colchetes ---------------------------

def test_b_evangelho_referencia_e_colchetes(missa):
    ev = None
    for b in _blocos(missa):
        cat = (getattr(b, "categoria", "") or "").lower()
        tit = (getattr(b, "titulo", "") or "").lower()
        if cat == "evangelho" or (tit == "evangelho"):
            ev = b
            break
    assert ev is not None, "bloco do Evangelho não encontrado"
    ref = getattr(ev, "referencia", "") or ""
    assert "Mt 13,24-43" in ref and "mais breve 13,24-30" in ref, f"referência inesperada: {ref!r}"
    versos = [str(getattr(v, "texto", "") or "") for v in (getattr(ev, "versiculos", None) or [])]
    corpo = " ".join(versos)
    assert "[" in corpo and "]" in corpo, "colchetes da forma breve não preservados no corpo do Evangelho"


# --------------------------- (c) preces numeradas ---------------------------

def test_c_oracao_fieis_intencoes_numeradas(missa):
    preces = next(_por_titulo(missa, "oração dos fiéis", "oracao dos fieis", "preces"), None)
    assert preces is not None, "bloco da Oração dos Fiéis não encontrado"
    numeradas = set()
    for t in _turnos(preces):
        m = re.match(r"^\s*([1-4])[\.\)]", str(getattr(t, "texto", "") or ""))
        if m:
            numeradas.add(m.group(1))
    assert len(numeradas) >= 4, f"esperado 4 intenções numeradas; achei {sorted(numeradas)}"


# --------------------------- (d) Canto Final: repetições ---------------------------

def test_d_canto_final_repeticoes_tantas_gracas(missa):
    canto = next(_por_titulo(missa, "canto final"), None)
    assert canto is not None, "bloco do Canto Final não encontrado"
    versos = _versos_estrofes(canto)
    ocorr = sum(1 for v in versos if "tantas graças" in v.lower())
    assert ocorr >= 2, f"repetições 'Tantas graças...' ausentes/insuficientes nas estrofes (achei {ocorr})"


# --------------------------- (e) momento de silêncio 1x ---------------------------

def test_e_momento_silencio_oracao_pessoal_unico(missa):
    # Conta BLOCOS standalone cujo título é a rubrica (um bloco com o texto repetido
    # em titulo+texto conta como 1). A duplicação real (antes E depois da antífona)
    # seria 2 blocos — o dedup determinístico + regra X garantem 1.
    alvo = "momento de silêncio para oração pessoal"
    blocos_rubrica = [
        b for b in _blocos(missa)
        if (getattr(b, "titulo", "") or "").strip().lower() == alvo
    ]
    assert len(blocos_rubrica) == 1, (
        f"bloco 'Momento de silêncio para oração pessoal' deve aparecer 1x; "
        f"apareceu {len(blocos_rubrica)}x"
    )
