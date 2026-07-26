"""Fluxo "montagem com conferência convergente" (passos 3–6 do redesenho).

3. MAPA VISUAL prévio (visão, não monta): lê o PDF e produz o mapa do folheto.
4. MONTAGEM só-multimodal (Sonnet + mapa). Falhou o multimodal → levanta exceção
   (o chamador agenda retry + alerta). Texto puro NUNCA publica por aqui.
5. Verificações em camadas: schema (no montar) + correções determinísticas +
   checagens estruturais contra o MAPA.
6. CONFERENTE visual independente com LAÇO: compara montagem × PDF, emite
   divergências acionáveis, corrige e reconfere (máx. 3 iterações). Convergiu
   limpo → aprovada; senão → não aprovada (chamador põe pendente_revisao + e-mail).

Modelos configuráveis por env (MODELO_MAPA, MODELO_CONFERENTE); se apontarem para
um modelo Gemini/Google e houver OPENROUTER_API_KEY, roteia via OpenRouter; senão
usa o modelo multimodal padrão (ANTHROPIC_MODEL_MM, ex.: claude-sonnet-5).
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

from app.schema.missa import Missa
from app.llm.prompts import SYSTEM_PROMPT, build_user_prompt_mm
from app.pipeline.structure_llm import (
    _run_coro, _montar_missa, _limpar_cercas,
    _corrigir_posicao_refrao, _inserir_repeticoes_estrofes,
    _limpar_numero_estrofe_orfao, _dedup_momento_silencio,
)

logger = logging.getLogger(__name__)

MAX_ITER_CONFERENCIA = int(os.getenv("CONFERENCIA_MAX_ITER", "3"))


# ---------------------------------------------------------------- modelos/roteamento
def _modelo(papel: str) -> str:
    padrao = os.getenv("ANTHROPIC_MODEL_MM", "claude-sonnet-5")
    if papel == "mapa":
        return os.getenv("MODELO_MAPA") or padrao
    if papel == "conferente":
        return os.getenv("MODELO_CONFERENTE") or padrao
    return padrao  # montagem


async def _gerar(papel: str, system: str, user: str, pdf_bytes: bytes) -> str:
    modelo = _modelo(papel)
    ehg = ("google/" in modelo) or ("gemini" in modelo.lower())
    if ehg and os.getenv("OPENROUTER_API_KEY"):
        from app.llm.openrouter_client import OpenRouterClient
        return await OpenRouterClient().gerar(system, user, pdf_bytes=pdf_bytes, model=modelo)
    from app.llm.factory import get_llm_client
    return await get_llm_client().gerar(system, user, pdf_bytes=pdf_bytes, model=modelo)


def _extrair_json(txt: str) -> dict:
    t = _limpar_cercas(txt or "")
    return json.loads(t)


# ------------------------------------------------------------------- passo 3: MAPA
SYSTEM_MAPA = (
    "Você é um analista de diagramação de folhetos litúrgicos católicos. NÃO monta "
    "a missa: apenas LÊ o PDF e descreve o que está impresso, como um mapa estrutural."
)
INSTR_MAPA = (
    "Leia o PDF do folheto e produza o MAPA DO FOLHETO em JSON, descrevendo o que está "
    "IMPRESSO (não invente). Campos:\n"
    '{"blocos":[{"ordem":int,"numero_impresso":int|null,"titulo":"...","secao":"...|null"}],\n'
    ' "formula_evangelho":"Proclamação|Conclusão",\n'
    ' "colchetes_forma_breve":{"presente":bool,"onde":"ex.: vv.44-46 do Evangelho"},\n'
    ' "repeticoes":[{"onde":"ex.: Canto Final","marca":"2x|//: ://","quantas":int|null}],\n'
    ' "aspas_discurso_direto":[{"onde":"ex.: Canto de Entrada; Evangelho v.44"}],\n'
    ' "oracao_eucaristica":{"titulo":"ex.: Oração Eucarística IV","prefacio_ou_subtitulo":"...|null","mysterium":"ex.: Mistério da fé!"},\n'
    ' "apendices":["ex.: Leituras da Semana"],\n'
    ' "antifonas":[{"titulo":"Antífona da Comunhão","apos":"ex.: Momento de silêncio"}],\n'
    ' "silencios":["ex.: Momento de silêncio para oração pessoal, antes da Antífona da Comunhão"],\n'
    ' "categoria_ou_tema":"ex.: Ano Jubilar Arquidiocesano|null"}\n'
    "Responda SOMENTE o JSON."
)


def gerar_mapa(pdf_bytes: bytes) -> dict:
    """Passo 3 — mapa visual do folheto (visão, não monta). Fail-soft: {} em erro."""
    try:
        bruto = _run_coro(_gerar("mapa", SYSTEM_MAPA, INSTR_MAPA, pdf_bytes))
        mapa = _extrair_json(bruto)
        logger.info("mapa: %d blocos, ev=%s, colchetes=%s, repeticoes=%d",
                    len(mapa.get("blocos") or []), mapa.get("formula_evangelho"),
                    (mapa.get("colchetes_forma_breve") or {}).get("presente"),
                    len(mapa.get("repeticoes") or []))
        return mapa
    except Exception as e:  # noqa: BLE001
        logger.warning("mapa visual falhou (%s) — segue sem contrato do mapa", str(e)[:160])
        return {}


def _mapa_para_contrato(mapa: dict) -> str:
    if not mapa:
        return ""
    return (
        "\n=== MAPA DO FOLHETO (contrato desta edição — respeite ao montar) ===\n"
        + json.dumps(mapa, ensure_ascii=False)
        + "\n=== FIM DO MAPA ===\n"
    )


# ------------------------------------------------------- passo 4: MONTAGEM só-MM
async def _montar_mm(pdf_bytes: bytes, texto_limpo: str, mapa: dict,
                     data_hint: Optional[str]) -> Missa:
    user = build_user_prompt_mm(texto_limpo, data_hint) + _mapa_para_contrato(mapa)
    bruto = _limpar_cercas(await _gerar("montagem", SYSTEM_PROMPT, user, pdf_bytes))
    try:
        return _montar_missa(json.loads(bruto))
    except Exception as e:  # noqa: BLE001
        from app.llm.prompts import build_correcao_prompt
        correcao = build_correcao_prompt(bruto, str(e))
        bruto2 = _limpar_cercas(await _gerar("montagem", SYSTEM_PROMPT, correcao, pdf_bytes))
        return _montar_missa(json.loads(bruto2))  # se falhar de novo, propaga (sem texto)


def montar_com_mapa(pdf_bytes: bytes, texto_limpo: str, mapa: dict,
                    data_hint: Optional[str] = None) -> Missa:
    """Passo 4 — montagem SÓ multimodal + correções determinísticas. RAISE em falha."""
    missa = _run_coro(_montar_mm(pdf_bytes, texto_limpo, mapa, data_hint))
    _corrigir_posicao_refrao(missa, texto_limpo)
    _inserir_repeticoes_estrofes(missa, texto_limpo)
    _limpar_numero_estrofe_orfao(missa)
    _dedup_momento_silencio(missa)
    return missa


# --------------------------------------------- passo 5: checagens estruturais vs mapa
def checar_estrutural_vs_mapa(missa: Missa, mapa: dict) -> list[dict]:
    """Divergências estruturais determinísticas entre montagem e mapa."""
    if not mapa:
        return []
    divs: list[dict] = []
    blocos = missa.blocos or []
    def acha(sub):
        sub = sub.lower()
        return next((b for b in blocos if sub in (getattr(b, "titulo", "") or "").lower()), None)

    cb = (mapa.get("colchetes_forma_breve") or {})
    if cb.get("presente"):
        ev = acha("evangelho")
        tem = ev is not None and "[" in json.dumps(
            [v.model_dump() if hasattr(v, "model_dump") else v for v in (getattr(ev, "versiculos", None) or [])],
            ensure_ascii=False)
        if not tem:
            divs.append({"severidade": "critica", "tipo": "texto", "local": f"Evangelho {cb.get('onde','')}",
                         "detalhe": "mapa indica colchetes de forma breve, ausentes na montagem"})
    for rep in (mapa.get("repeticoes") or []):
        onde = (rep.get("onde") or "")
        b = acha(onde) if onde else None
        if b is not None and getattr(b, "tipo", None) == "canto":
            estr = getattr(b, "estrofes", None) or []
            # heurística: se o mapa diz repetição e nenhuma estrofe repete linha, acusa
            achou = any(len(e) != len(set(e)) for e in estr)
            if estr and not achou:
                divs.append({"severidade": "baixa", "tipo": "texto", "local": onde,
                             "detalhe": f"mapa indica repetição ({rep.get('marca')}), não encontrada nas estrofes"})
    # silêncios do mapa devem ter bloco correspondente na montagem
    def _tem_silencio():
        return any("silênci" in (getattr(b, "titulo", "") or "").lower()
                   or "silenci" in (getattr(b, "titulo", "") or "").lower()
                   for b in blocos)
    sils = mapa.get("silencios") or []
    # o mapa às vezes lista 2 (Homilia + oração pessoal); exige ao menos 1 bloco de silêncio
    if sils and not _tem_silencio():
        divs.append({"severidade": "critica", "tipo": "bloco",
                     "local": (sils[0] if isinstance(sils[0], str) else str(sils[0])),
                     "detalhe": "mapa indica Momento de silêncio impresso, ausente como bloco na montagem"})
    # tema/subtítulo impresso (ex.: 'Ano Jubilar Arquidiocesano') deve aparecer
    tema = mapa.get("categoria_ou_tema")
    if tema and isinstance(tema, str) and tema.strip().lower() not in ("null", "none", ""):
        alvo = " ".join(str(x or "") for x in [
            getattr(missa, "categoria", ""), getattr(missa, "observacoes", ""),
            getattr(missa, "descricao", ""), getattr(missa, "titulo_celebracao", ""),
        ] + [getattr(b, "subtitulo", "") or "" for b in blocos]).lower()
        chave = re.sub(r"[^0-9a-zà-úãõâêôçáéíóú ]", "", tema.lower()).strip()
        if chave and chave[:20] not in alvo:
            divs.append({"severidade": "baixa", "tipo": "texto", "local": "tema/categoria",
                         "esperado_pdf": tema,
                         "detalhe": f"tema impresso no folheto ('{tema}') não aparece na categoria/observações/subtítulo"})
    return divs


# --------------------------------------------------- passo 6: CONFERENTE com laço
SYSTEM_CONF = (
    "Você é um conferente rigoroso e independente de fidelidade litúrgica. Compara a "
    "MONTAGEM (JSON) com o PDF OFICIAL e emite divergências ACIONÁVEIS. Conservador: "
    "na dúvida, não acuse."
)
INSTR_CONF = (
    "O PDF anexado é o folheto OFICIAL (fonte da verdade). Abaixo, a MONTAGEM (JSON).\n"
    "Aponte divergências REAIS de conteúdo (texto/ref/rubrica/título/bloco/fórmula do "
    "Evangelho/número de versículo/colchetes de forma breve/aspas de discurso direto/"
    "numeração das preces/ordem de blocos como no impresso).\n"
    "IGNORE: formatação, itálico, cores, quebras de linha, refrão reprisado guardado uma "
    "vez, resposta das preces repetida, selos de postura.\n"
    'Responda SOMENTE JSON: {"divergencias":[{"severidade":"critica|baixa","local":"onde",'
    '"esperado_pdf":"...","encontrado_montagem":"...","detalhe":"..."}]}'
)


def _montagem_json(missa: Missa) -> str:
    return json.dumps(missa.model_dump(), ensure_ascii=False)


def conferir(pdf_bytes: bytes, missa: Missa) -> list[dict]:
    """Passo 6 (conferência) — retorna lista de divergências. Fail-soft: [] em erro."""
    try:
        user = INSTR_CONF + "\n\n=== MONTAGEM (JSON) ===\n" + _montagem_json(missa)
        data = _extrair_json(_run_coro(_gerar("conferente", SYSTEM_CONF, user, pdf_bytes)))
        return data.get("divergencias") or []
    except Exception as e:  # noqa: BLE001
        logger.warning("conferente falhou (%s) — trata como sem divergências", str(e)[:160])
        return []


def _corrigir(pdf_bytes: bytes, texto_limpo: str, mapa: dict, missa: Missa,
              divergencias: list[dict], data_hint: Optional[str]) -> Missa:
    divs = json.dumps(divergencias, ensure_ascii=False)
    user = (
        build_user_prompt_mm(texto_limpo, data_hint) + _mapa_para_contrato(mapa)
        + "\n=== MONTAGEM ATUAL (corrija EXATAMENTE as divergências abaixo, mantenha o resto) ===\n"
        + _montagem_json(missa)
        + "\n=== DIVERGÊNCIAS A CORRIGIR ===\n" + divs
        + "\nDevolva o JSON COMPLETO da missa já corrigido. Só o JSON."
    )
    bruto = _limpar_cercas(_run_coro(_gerar("montagem", SYSTEM_PROMPT, user, pdf_bytes)))
    nova = _montar_missa(json.loads(bruto))
    _corrigir_posicao_refrao(nova, texto_limpo)
    _inserir_repeticoes_estrofes(nova, texto_limpo)
    _limpar_numero_estrofe_orfao(nova)
    _dedup_momento_silencio(nova)
    return nova


def montar_com_conferencia(pdf_bytes: bytes, texto_limpo: str,
                           data_hint: Optional[str] = None) -> tuple[Missa, dict]:
    """Orquestra os passos 3–6. Retorna (missa, meta).

    meta = {conferida:bool, iteracoes:int, divergencias_restantes:[...], mapa:{...}}
    RAISE se a montagem multimodal falhar (passo 4) — o chamador agenda retry/alerta;
    NUNCA cai para texto puro aqui.
    """
    mapa = gerar_mapa(pdf_bytes)                                   # passo 3
    missa = montar_com_mapa(pdf_bytes, texto_limpo, mapa, data_hint)  # passo 4 (+5 determ.)

    iteracoes = 0
    divergencias: list[dict] = []
    for i in range(MAX_ITER_CONFERENCIA):
        estruturais = checar_estrutural_vs_mapa(missa, mapa)      # passo 5 (vs mapa)
        visuais = conferir(pdf_bytes, missa)                      # passo 6 (visão)
        divergencias = estruturais + visuais
        criticas = [d for d in divergencias if str(d.get("severidade", "")).lower() == "critica"]
        if not criticas:
            logger.info("conferência convergiu em %d iteração(ões)", i)
            return missa, {"conferida": True, "iteracoes": i,
                           "divergencias_restantes": divergencias, "mapa": mapa}
        iteracoes = i + 1
        logger.info("iteração %d: %d crítica(s) (+%d baixa) — corrigindo",
                    iteracoes, len(criticas), len(divergencias) - len(criticas))
        try:
            # corrige TODAS as divergências (críticas gatilham o laço; baixas pegam carona)
            missa = _corrigir(pdf_bytes, texto_limpo, mapa, missa, divergencias, data_hint)
        except Exception:
            logger.exception("correção da iteração %d falhou — encerra laço", iteracoes)
            break
    # Não convergiu
    return missa, {"conferida": False, "iteracoes": iteracoes,
                   "divergencias_restantes": divergencias, "mapa": mapa}
