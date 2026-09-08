"""Fluxo "montagem com conferência convergente" (passos 3–6 do redesenho).

3. MAPA LITÚRGICO prévio (visão, não monta): lê o PDF e produz o mapa do conteúdo
   e da hierarquia litúrgica, sem avaliar o projeto editorial.
4. MONTAGEM só-multimodal (Sonnet + mapa). Falhou o multimodal → levanta exceção
   (o chamador agenda retry + alerta). Texto puro NUNCA publica por aqui.
5. Verificações em camadas: schema (no montar) + correções determinísticas +
   checagens de conteúdo e hierarquia litúrgica contra o MAPA.
6. CONFERENTE independente com LAÇO: compara o conteúdo litúrgico da montagem
   com o PDF, emite
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
from typing import Optional

from app.schema.missa import Missa
from app.llm.prompts import SYSTEM_PROMPT, build_user_prompt_mm
from app.pipeline.structure_llm import (
    _run_coro, _montar_missa, _limpar_cercas,
    _corrigir_posicao_refrao, _inserir_repeticoes_estrofes,
    _limpar_numero_estrofe_orfao, _dedup_momento_silencio,
)

logger = logging.getLogger(__name__)

# O limite é parte do contrato operacional: configuração não pode aumentá-lo
# silenciosamente acima das três tentativas aprovadas para esta etapa.
MAX_ITER_CONFERENCIA = max(1, min(int(os.getenv("CONFERENCIA_MAX_ITER", "3")), 3))


class ConferenciaIndisponivel(RuntimeError):
    """A fonte de verdade ou o crítico não pôde ser consultado.

    A ausência de uma crítica independente não é evidência de aprovação.  O
    chamador transforma esta exceção em ``pendente_revisao`` e preserva uma
    publicação anterior que já tenha sido aprovada.
    """


def _contrato_gauntlet() -> dict:
    """Evidência persistida do contrato usado nesta execução.

    O contrato torna auditável o que foi aceito: o PDF é a referência; a métrica
    não inclui diagramação, apenas texto e hierarquia litúrgicos; e o limite
    automático é de três correções antes de retenção humana.
    """
    return {
        "objetivo": "fidelidade do conteúdo e da hierarquia litúrgicos ao PDF oficial",
        "referencia": "PDF oficial da mesma edição",
        "metrica": "zero divergências litúrgicas pendentes",
        "limite_iteracoes": MAX_ITER_CONFERENCIA,
        "fora_do_escopo": [
            "projeto editorial", "diagramação", "paginação", "cores", "tipografia", "imagens",
        ],
        "papeis": {
            "construtor": "montagem",
            "critico": "conferente em contexto separado, sem o raciocínio do construtor",
            "referencia": "mapa litúrgico do PDF + texto extraído do PDF",
        },
    }


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
        return await OpenRouterClient().gerar(system, user, pdf_bytes=pdf_bytes, model=modelo, contexto=f"conv:{papel}")
    from app.llm.factory import get_llm_client
    return await get_llm_client().gerar(system, user, pdf_bytes=pdf_bytes, model=modelo, contexto=f"conv:{papel}")


def _extrair_json(txt: str) -> dict:
    t = _limpar_cercas(txt or "")
    return json.loads(t)


# ------------------------------------------------------------------- passo 3: MAPA
SYSTEM_MAPA = (
    "Você é um analista de conteúdo litúrgico católico. NÃO monta a missa: apenas "
    "LÊ o PDF e descreve seu conteúdo e sua hierarquia litúrgica. Não avalie nem "
    "registre elementos de projeto editorial, diagramação ou paginação."
)
INSTR_MAPA = (
    "Leia o PDF e produza o MAPA LITÚRGICO em JSON, descrevendo somente o conteúdo "
    "litúrgico impresso e sua hierarquia (não invente). Ignore capa, logotipos, créditos "
    "editoriais, cores, fontes, colunas, imagens, cabeçalhos/rodapés gráficos, números e "
    "quebras de página. Campos:\n"
    '{"blocos":[{"ordem":int,"numero_impresso":int|null,"titulo":"...","secao":"...|null"}],\n'
    ' "formula_evangelho":"Proclamação|Conclusão",\n'
    ' "colchetes_forma_breve":{"presente":bool,"onde":"ex.: vv.44-46 do Evangelho"},\n'
    ' "repeticoes":[{"onde":"ex.: Canto Final","marca":"2x|//: ://","quantas":int|null}],\n'
    ' "aspas_discurso_direto":[{"onde":"ex.: Canto de Entrada; Evangelho v.44"}],\n'
    ' "oracao_eucaristica":{"titulo":"ex.: Oração Eucarística IV","prefacio_ou_subtitulo":"...|null","mysterium":"ex.: Mistério da fé!"},\n'
    ' "apendices":["ex.: Leituras da Semana"],\n'
    ' "antifonas":[{"titulo":"Antífona da Comunhão","apos":"ex.: Momento de silêncio"}],\n'
    ' "silencios":["ex.: Momento de silêncio para oração pessoal, antes da Antífona da Comunhão"]}\n'
    "Responda SOMENTE o JSON."
)


def gerar_mapa(pdf_bytes: bytes) -> dict:
    """Passo 3 — obtém o contrato litúrgico do PDF; falha fecha o gate."""
    try:
        bruto = _run_coro(_gerar("mapa", SYSTEM_MAPA, INSTR_MAPA, pdf_bytes))
        mapa = _extrair_json(bruto)
        logger.info("mapa: %d blocos, ev=%s, colchetes=%s, repeticoes=%d",
                    len(mapa.get("blocos") or []), mapa.get("formula_evangelho"),
                    (mapa.get("colchetes_forma_breve") or {}).get("presente"),
                    len(mapa.get("repeticoes") or []))
        if not isinstance(mapa, dict) or not isinstance(mapa.get("blocos"), list):
            raise ValueError("mapa sem a lista obrigatória de blocos")
        return mapa
    except Exception as e:  # noqa: BLE001
        logger.warning("mapa litúrgico falhou (%s) — publicação bloqueada", str(e)[:160])
        raise ConferenciaIndisponivel("não foi possível obter o mapa litúrgico do PDF") from e


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
    return divs


def checar_texto_liturgico_vs_fonte(texto_limpo: str, missa: Missa) -> list[dict]:
    """Crítico determinístico: não aceita palavras inventadas fora do PDF.

    Esta camada é independente do julgamento multimodal. Ela só lê o texto
    litúrgico estruturado da montagem e o texto extraído do PDF; não inspeciona
    layout, fontes, cores, páginas ou qualquer elemento editorial.
    """
    try:
        from app.services.verificador_lexical import verificar_lexico

        blocos = [b.model_dump() for b in (missa.blocos or [])]
        suspeitas = verificar_lexico(texto_limpo, blocos, getattr(missa, "descricao", None))
        return [
            {
                "severidade": "critica",
                "escopo": "conteudo_liturgico",
                "local": f"{s['bloco']} · {s['campo']}",
                "esperado_pdf": "palavra presente no texto litúrgico do PDF",
                "encontrado_montagem": s["palavra"],
                "detalhe": f"palavra fora do texto-fonte: {s['palavra']}",
            }
            for s in suspeitas
        ]
    except Exception as e:  # noqa: BLE001
        logger.warning("checagem lexical falhou (%s) — publicação bloqueada", str(e)[:160])
        raise ConferenciaIndisponivel("não foi possível conferir o texto litúrgico contra o PDF") from e


# --------------------------------------------------- passo 6: CONFERENTE com laço
SYSTEM_CONF = (
    "Você é um conferente rigoroso e independente de fidelidade litúrgica. Compara a "
    "MONTAGEM (JSON) com o PDF OFICIAL e emite divergências ACIONÁVEIS apenas de "
    "conteúdo ou hierarquia litúrgica. Conservador: na dúvida, não acuse."
)
INSTR_CONF = (
    "O PDF anexado é o folheto OFICIAL (fonte da verdade). Abaixo, a MONTAGEM (JSON).\n"
    "Aponte somente divergências REAIS de conteúdo ou hierarquia litúrgica: texto, "
    "referência, rubrica, título litúrgico, seção, bloco, fórmula do Evangelho, número "
    "de versículo, colchetes de forma breve, aspas de discurso direto, numeração das "
    "preces e ordem dos blocos litúrgicos.\n"
    "IGNORE TOTALMENTE: capa, logotipos, créditos editoriais, tipografia, cores, imagens, "
    "colunas, alinhamento, espaçamento, quebras de linha ou página, cabeçalhos/rodapés "
    "gráficos, numeração de páginas, selos de postura e outros elementos editoriais. "
    "Também ignore uma repetição visual do refrão ou resposta quando a montagem a guarda "
    "corretamente uma única vez.\n"
    'Responda SOMENTE JSON: {"divergencias":[{"severidade":"critica|baixa","escopo":"conteudo_liturgico|hierarquia_liturgica","local":"onde",'
    '"esperado_pdf":"...","encontrado_montagem":"...","detalhe":"..."}]}'
)


def _montagem_json(missa: Missa) -> str:
    return json.dumps(missa.model_dump(), ensure_ascii=False)


def conferir(pdf_bytes: bytes, missa: Missa) -> list[dict]:
    """Passo 6 — crítica independente; indisponibilidade nunca aprova a missa."""
    try:
        user = INSTR_CONF + "\n\n=== MONTAGEM (JSON) ===\n" + _montagem_json(missa)
        data = _extrair_json(_run_coro(_gerar("conferente", SYSTEM_CONF, user, pdf_bytes)))
        divergencias = data.get("divergencias")
        if not isinstance(divergencias, list):
            raise ValueError("resposta do conferente sem lista de divergências")
        return divergencias
    except Exception as e:  # noqa: BLE001
        logger.warning("conferente falhou (%s) — publicação bloqueada", str(e)[:160])
        raise ConferenciaIndisponivel("não foi possível executar a crítica independente") from e


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

    meta = {conferida:bool, iteracoes:int, divergencias_restantes:[...], mapa:{...}, contrato:{...}}
    RAISE se a montagem multimodal falhar (passo 4) — o chamador agenda retry/alerta;
    NUNCA cai para texto puro aqui.
    """
    mapa = gerar_mapa(pdf_bytes)                                   # passo 3
    missa = montar_com_mapa(pdf_bytes, texto_limpo, mapa, data_hint)  # passo 4 (+5 determ.)

    iteracoes = 0
    divergencias: list[dict] = []
    for i in range(MAX_ITER_CONFERENCIA):
        estruturais = checar_estrutural_vs_mapa(missa, mapa)      # passo 5 (vs mapa)
        textuais = checar_texto_liturgico_vs_fonte(texto_limpo, missa)
        visuais = conferir(pdf_bytes, missa)                      # passo 6 (visão)
        divergencias = estruturais + textuais + visuais
        # O conferente recebe a instrução de devolver somente divergências litúrgicas.
        # Por isso nenhuma delas é "aceitável": conteúdo/hierarquia só convergem quando
        # a lista fica vazia. Elementos editoriais não entram nessa lista.
        if not divergencias:
            logger.info("conferência convergiu em %d iteração(ões)", i)
            return missa, {"conferida": True, "iteracoes": i,
                           "divergencias_restantes": divergencias, "mapa": mapa,
                           "contrato": _contrato_gauntlet()}
        iteracoes = i + 1
        logger.info("iteração %d: %d divergência(s) litúrgica(s) — corrigindo",
                    iteracoes, len(divergencias))
        try:
            # corrige TODAS as divergências (críticas gatilham o laço; baixas pegam carona)
            missa = _corrigir(pdf_bytes, texto_limpo, mapa, missa, divergencias, data_hint)
        except Exception:
            logger.exception("correção da iteração %d falhou — encerra laço", iteracoes)
            break
    # Não convergiu
    return missa, {"conferida": False, "iteracoes": iteracoes,
                   "divergencias_restantes": divergencias, "mapa": mapa,
                   "contrato": _contrato_gauntlet()}
