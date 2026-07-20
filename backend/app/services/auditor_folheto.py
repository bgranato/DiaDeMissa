"""Gate de fidelidade PDF × montagem (pilar 2 da solução definitiva).

Um segundo modelo (Sonnet, independente do que montou) lê o PDF OFICIAL e a
MONTAGEM (JSON) e aponta divergências REAIS de conteúdo. Se houver divergência
CRÍTICA, a missa vai para `pendente_revisao` (escondida do fiel até revisão) —
assim a fidelidade é garantida por máquina, sem depender de olho humano.

Conservador de propósito: só CRÍTICA bloqueia; formatação/ordem/refrão-repetido
não contam. Em qualquer falha (API, JSON inválido), NÃO bloqueia (fail-open) para
nunca esconder uma missa boa por erro do próprio gate.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

SYSTEM = (
    "Você é um auditor rigoroso de fidelidade litúrgica. Compara a MONTAGEM (JSON) "
    "de uma missa com o PDF OFICIAL do folheto e aponta APENAS divergências REAIS "
    "de conteúdo. Seja conservador: na dúvida, NÃO acuse."
)

INSTR = (
    "O PDF anexado é o folheto OFICIAL (fonte da verdade). Abaixo está a MONTAGEM gerada (JSON).\n"
    "Encontre divergências REAIS de conteúdo entre a montagem e o PDF.\n\n"
    "CONTA como ERRO (severidade 'critica'):\n"
    "- oração/leitura/salmo/versículo/estrofe/refrão com texto FALTANDO, TROCADO ou ALTERADO;\n"
    "- referência bíblica errada ou faltando (ex.: PDF traz 'Ct 3,1-4a' e a montagem tem 'Ct 3,14a');\n"
    "- rubrica entre parênteses do PDF ausente na montagem (ex.: '(todos se inclinam...)', '(O Presidente continua)');\n"
    "- título de bloco trocado; bloco inteiro faltando.\n\n"
    "NÃO conta como erro (IGNORE): formatação, pontuação, aspas, itálico, cores, ordem, quebras de "
    "linha; o refrão reprisado dentro das estrofes que a montagem guarda uma vez; a resposta das preces "
    "repetida a cada intenção; as posturais '(De pé)/(Sentados)/(Sentado)' (viram selo, não texto); "
    "acréscimos litúrgicos corretos.\n\n"
    'Responda SOMENTE JSON: {"divergencias":[{"severidade":"critica|baixa","tipo":"referencia|rubrica|texto|titulo|bloco",'
    '"local":"onde no folheto","esperado_pdf":"...","encontrado_montagem":"...","detalhe":"..."}]}'
)


def usar_gate_pdf() -> bool:
    return os.getenv("USAR_GATE_PDF", "0").strip().lower() in ("1", "true", "yes", "on")


def _montagem_json(missa_db) -> str:
    blocos = []
    for b in missa_db.blocos:
        ce = b.conteudo_estruturado
        if isinstance(ce, str):
            try:
                ce = json.loads(ce)
            except Exception:
                ce = {"texto": ce}
        blocos.append(ce or {"titulo": b.titulo, "referencia": b.referencia})
    return json.dumps({
        "titulo_celebracao": missa_db.celebracao,
        "descricao": missa_db.descricao,
        "observacoes": missa_db.observacoes,
        "creditos_cantos": missa_db.creditos_cantos,
        "blocos": blocos,
    }, ensure_ascii=False)


def _extrair_json(txt: str) -> dict[str, Any]:
    t = txt.strip()
    t = re.sub(r"^```[a-zA-Z]*\n", "", t)
    t = re.sub(r"\n```$", "", t).strip()
    return json.loads(t)


async def _chamar(pdf_bytes: bytes, montagem_json: str):
    from app.llm.factory import get_llm_client
    client = get_llm_client()
    modelo = os.getenv("ANTHROPIC_MODEL_GATE", "claude-sonnet-5")
    user = INSTR + "\n\n=== MONTAGEM (JSON) ===\n" + montagem_json
    bruto = await client.gerar(SYSTEM, user, pdf_bytes=pdf_bytes, model=modelo)
    return _extrair_json(bruto)


def auditar_contra_pdf(missa_db, pdf_bytes: bytes) -> dict:
    """Retorna {ok, criticas:[...], todas:[...]}. ok=False se houver CRÍTICA.

    Fail-open: em qualquer erro, retorna ok=True (não bloqueia) e loga.
    """
    try:
        data = _chamar_sync(pdf_bytes, _montagem_json(missa_db))
        divs = data.get("divergencias") or []
        criticas = [d for d in divs if str(d.get("severidade", "")).lower() == "critica"]
        return {"ok": not criticas, "criticas": criticas, "todas": divs}
    except Exception as e:
        logger.exception("Gate PDF falhou (fail-open, não bloqueia): %s", str(e)[:200])
        return {"ok": True, "criticas": [], "todas": [], "erro": str(e)[:200]}


def _chamar_sync(pdf_bytes: bytes, montagem_json: str):
    try:
        return asyncio.run(_chamar(pdf_bytes, montagem_json))
    except RuntimeError:
        # Já dentro de um event loop: roda em thread separada.
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(lambda: asyncio.run(_chamar(pdf_bytes, montagem_json))).result()
