"""Testes do verificador léxico determinístico (app/services/verificador_lexical.py)."""
from __future__ import annotations

import os
import pytest

from app.services.verificador_lexical import verificar_lexico, verificar_aspas


FONTE = "Curai os doentes, ressuscitai os mortos. De graça recebestes, de graça deveis dar!"


def test_devis_flagra():
    """Caso real 06-14: montagem com 'devis' (typo de 'deveis') deve ser flagrada."""
    montagem = [{"titulo": "Evangelho", "tipo": "leitura",
                 "versiculos": [{"numero": 8, "texto": "De graça recebestes, de graça devis dar!"}]}]
    sus = verificar_lexico(FONTE, montagem, None)
    palavras = [s["palavra"] for s in sus]
    assert "devis" in palavras, f"'devis' deveria ser flagrada; suspeitas={palavras}"


def test_montagem_fiel_nao_flagra():
    """Montagem fiel ao fonte não gera nenhuma suspeita."""
    montagem = [{"titulo": "Evangelho", "tipo": "leitura",
                 "versiculos": [{"numero": 8, "texto": "De graça recebestes, de graça deveis dar!"}]}]
    assert verificar_lexico(FONTE, montagem, None) == []


def test_truncagem_da_extracao_nao_flagra():
    """A extração do PDF trunca palavras acentuadas ('aclamações' -> 'aclamaçõ' no
    fonte). A montagem correta ('aclamações') NÃO pode ser flagrada (tolerância)."""
    fonte = "cantar as aclamaçõ com alegria e as oraçõ do povo"
    montagem = [{"titulo": "Canto", "tipo": "canto",
                 "estrofes": [["cantar as aclamações com alegria", "e as orações do povo"]]}]
    assert verificar_lexico(fonte, montagem, None) == []


def test_ignora_numeros_e_siglas():
    """Números e siglas de 1-2 letras não geram suspeita."""
    montagem = [{"titulo": "Salmo", "tipo": "salmo",
                 "turnos": [{"falante": "L", "texto": "Sl 23 P T L 1 2 3"}]}]
    # 'sl' tem 2 letras (ignorado); números ignorados
    assert verificar_lexico("qualquer texto fonte aqui", montagem, None) == []


def test_recompoe_palavra_quebrada_por_hifen_de_linha_no_pdf():
    fonte = "pedimos: aceitai-nos também com vosso Filho e dai-\n-nos o seu Espírito"
    montagem = [{"titulo": "Oração", "turnos": [{"texto": "dai-nos o seu Espírito"}]}]

    assert verificar_lexico(fonte, montagem, None) == []


# --- Aspas do discurso direto (regra L) ---

def test_aspas_dropadas_geram_deficit():
    fonte = 'proclamava Jesus: “Devo anunciar às cidades o Reino de Deus”, e partiu.'
    montagem = [{"titulo": "Canto", "estrofes": [["Devo anunciar às cidades o Reino de Deus, proclamava Jesus."]]}]
    assert verificar_aspas(fonte, montagem) >= 2  # 2 aspas curvas dropadas


def test_aspas_preservadas_sem_deficit():
    fonte = 'proclamava Jesus: “Devo anunciar às cidades o Reino de Deus”, e partiu.'
    montagem = [{"titulo": "Canto", "estrofes": [['“Devo anunciar às cidades o Reino de Deus”, proclamava Jesus.']]}]
    assert verificar_aspas(fonte, montagem) == 0


# --- Integração: 9 missas do banco (requer DB + PDFs; pula sem eles) ---

_TEM_DB = bool(os.getenv("RODAR_TESTES_DB")) or os.path.exists("/var/lib/diademissa/missa_hoje.db")


@pytest.mark.skipif(not _TEM_DB, reason="requer banco de produção + PDFs arquivados")
def test_9_missas_baixo_falso_positivo():
    """As 9 missas corrigidas devem gerar FP muito baixo. Os poucos residuais são
    ARTEFATOS DA EXTRAÇÃO-FONTE (ex.: 'bninguém' colado, 'ação' só como substring) —
    por isso o modo padrão é ALERTAR, não bloquear. O teste trava regressão: FP total
    não pode passar de 2, e nenhuma missa pode ter mais de 1 suspeita."""
    import json
    from app.core.database import SessionLocal
    from app.models.missa import Missa, BlocoLiturgico
    from app.pipeline.download import CACHE_DIR
    from app.pipeline.extract import extrair_texto_estruturado
    from app.pipeline.clean import limpar

    datas = ["2026-05-17", "2026-05-24", "2026-06-07", "2026-06-14", "2026-06-21",
             "2026-06-28", "2026-07-05", "2026-07-12", "2026-07-19"]
    db = SessionLocal()
    try:
        total = 0
        for d in datas:
            m = db.query(Missa).filter(Missa.data == d).first()
            if not m:
                continue
            txt = limpar(extrair_texto_estruturado(CACHE_DIR / "archive" / (d + ".pdf")))
            blocos = []
            for b in db.query(BlocoLiturgico).filter(BlocoLiturgico.missa_id == m.id).all():
                c = b.conteudo_estruturado
                blocos.append(c if isinstance(c, dict) else json.loads(c or "{}"))
            sus = verificar_lexico(txt, blocos, m.descricao)
            assert len(sus) <= 1, f"{d}: FP alto ({[s['palavra'] for s in sus]})"
            total += len(sus)
        assert total <= 2, f"FP total das 9 missas subiu para {total} (esperado <= 2)"
    finally:
        db.close()
