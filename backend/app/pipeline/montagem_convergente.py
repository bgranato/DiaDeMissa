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
    _run_coro, _montar_missa, _limpar_cercas, _norm_busca,
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
        "referencia": "PDF oficial da mesma edição — versão Celular",
        "metrica": "zero divergências litúrgicas pendentes",
        "limite_iteracoes": MAX_ITER_CONFERENCIA,
        "fora_do_escopo": [
            "projeto editorial", "diagramação", "paginação", "cores", "tipografia", "imagens",
        ],
        "papeis": {
            "construtor": "montagem a partir do PDF oficial versão Celular",
            "critico": "conferente em contexto separado, sem o raciocínio do construtor",
            "referencia": "mapa litúrgico + texto extraído do PDF Celular",
        },
        "fontes": {
            "principal": "Celular: única fonte de extração e estruturação",
            "secundaria": "Celebrante: conferência de falas do presidente, rubricas e Oração Eucarística",
            "vedada_para_extracao": "Assembleia: nunca usada como fallback ou fonte de extração",
        },
    }


# ---------------------------------------------------------------- modelos/roteamento
def _modelo(papel: str) -> str:
    # O default muda com o provider: o Gemini usa seu próprio catálogo de modelos
    # (gemini-2.0-flash, gemini-3.6-flash) — pedir "claude-sonnet-5" para o Gemini
    # retorna 404. Anthropic e DeepSeek mantêm o histórico.
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    if provider == "gemini":
        padrao = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    elif provider == "deepseek":
        padrao = os.getenv("DEEPSEEK_MODEL_MM", "deepseek-chat")
    else:
        padrao = os.getenv("ANTHROPIC_MODEL_MM", "claude-sonnet-5")
    if papel == "mapa":
        return os.getenv("MODELO_MAPA") or padrao
    if papel.startswith("conferente"):
        return os.getenv("MODELO_CONFERENTE") or padrao
    return padrao  # montagem


def _pdf_para_provedor(pdf_bytes: bytes) -> bytes:
    """Remove só espaço em branco antes do cabeçalho para transporte ao LLM.

    Alguns PDFs oficiais linearizados vêm com CR/LF/espaços antes de ``%PDF``.
    Isso é aceito pelos leitores de PDF, mas certos provedores multimodais exigem
    que o cabeçalho esteja no byte zero. A normalização é uma cópia exclusiva do
    transporte: o PDF bruto continua sendo o que é arquivado, hasheado e usado
    como referência auditável do Gauntlet.
    """
    if pdf_bytes.startswith(b"%PDF-"):
        return pdf_bytes
    normalizado = pdf_bytes.lstrip(b"\x09\x0a\x0c\x0d\x20")
    if normalizado.startswith(b"%PDF-"):
        logger.info("PDF oficial normalizado para transporte ao provedor (%d bytes de prefixo)",
                    len(pdf_bytes) - len(normalizado))
        return normalizado
    return pdf_bytes


async def _gerar(papel: str, system: str, user: str, pdf_bytes: bytes) -> str:
    modelo = _modelo(papel)
    pdf_provedor = _pdf_para_provedor(pdf_bytes)
    ehg = ("google/" in modelo) or ("gemini" in modelo.lower())
    # O OpenRouter é compatibilidade para críticos Gemini configurados sobre um
    # pipeline Anthropic. Quando o provedor escolhido é Gemini, ele tem
    # precedência e usa a API direta mesmo que uma chave legada do OpenRouter
    # permaneça no ambiente.
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    if ehg and provider != "gemini" and os.getenv("OPENROUTER_API_KEY"):
        from app.llm.openrouter_client import OpenRouterClient
        return await OpenRouterClient().gerar(system, user, pdf_bytes=pdf_provedor, model=modelo, contexto=f"conv:{papel}")
    from app.llm.factory import get_llm_client
    return await get_llm_client().gerar(system, user, pdf_bytes=pdf_provedor, model=modelo, contexto=f"conv:{papel}")


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


def _sincronizar_numero_folheto(missa: Missa, mapa: dict) -> None:
    """Realinha `numero_folheto` de cada bloco com o `numero_impresso` do mapa.

    DETERMINÍSTICO (independe do LLM): o mapa é a leitura do PDF na etapa 3, então
    é a fonte de verdade da numeração impressa. Regras:
    - Bloco do mapa com `numero_impresso` → por título normalizado, o bloco
      correspondente herda esse número (alinhamento fiel ao mapa).
    - Bloco do mapa com `numero_impresso: null` (rubrica, antífona anexada, apêndice)
      → o bloco correspondente fica SEM número (ganha None). Nunca inventamos número.
    - Bloco da montagem SEM correspondência no mapa é preservado como veio: cabe ao
      revisor (`checar_numeracao_vs_mapa`) acusar número suspeito — aqui não zeramos
      nada legítimo que o mapa tenha omitido de propósito.
    Blocos seção (sem o campo) são ignorados. O vínculo é por título normalizado,
    com suporte a títulos repetidos (antífonas iguais em cantos diferentes).
    """
    if not mapa or not getattr(missa, "blocos", None):
        return
    numeros_por_titulo: dict[str, list[Optional[int]]] = {}
    for mb in mapa.get("blocos") or []:
        t = _norm_busca(mb.get("titulo") or "")
        if not t:
            continue
        numeros_por_titulo.setdefault(t, []).append(mb.get("numero_impresso"))
    usados: dict[str, int] = {}
    for bloco in missa.blocos:
        if not hasattr(bloco, "numero_folheto"):
            continue  # bloco de seção não tem numeração de folheto
        t = _norm_busca(getattr(bloco, "titulo", "") or "")
        if not t or t not in numeros_por_titulo:
            continue
        k = usados.get(t, 0)
        candidatos = numeros_por_titulo[t]
        bloco.numero_folheto = candidatos[k % len(candidatos)]
        usados[t] = k + 1


# ------------------------------------------------------- passo 4: MONTAGEM só-MM
async def _montar_mm(pdf_bytes: bytes, texto_limpo: str, mapa: dict,
                     data_hint: Optional[str]) -> Missa:
    user = (
        "O PDF anexado é a versão oficial CELULAR e é a ÚNICA fonte para extrair e "
        "estruturar a missa. Gere blocos estruturados com seção, número, tipo, "
        "falante, texto, referência e postura. Não use conhecimento externo nem "
        "qualquer versão Assembleia.\n"
        + build_user_prompt_mm(texto_limpo, data_hint)
        + _mapa_para_contrato(mapa)
    )
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
    # A numeração vem do mapa (fonte da verdade), nunca da inferência do LLM.
    _sincronizar_numero_folheto(missa, mapa)
    return missa


# --------------------------------------------- passo 5: checagens estruturais vs mapa
def checar_numeracao_vs_mapa(missa: Missa, mapa: dict) -> list[dict]:
    """Numeração do folheto: nenhum bloco pode inventar, duplicar ou regredir número.

    O mapa (etapa 3) é a fonte da verdade da numeração impressa. Valida:
    - número no bloco sem `numero_impresso` correspondente no mapa (inventado);
    - número duplicado entre blocos (o folheto nunca repete numeração);
    - numeração em ordem decrescente entre blocos que SÃO numerados (o folheto
      sempre cresce; blocos sem número no meio não podem quebrar a sequência);
    - bloco numerado no mapa ausente na montagem (omissão estrutural).
    Números com pulo (ex.: 1, 2, 4) são aceitos: alguns folhetos pulam números.
    """
    if not mapa or not getattr(missa, "blocos", None):
        return []
    divs: list[dict] = []
    blocos = missa.blocos or []

    # 1) números que o mapa conhece, por título normalizado (com repetidos)
    numeros_mapa: dict[str, list[Optional[int]]] = {}
    for mb in mapa.get("blocos") or []:
        t = _norm_busca(mb.get("titulo") or "")
        if not t:
            continue
        numeros_mapa.setdefault(t, []).append(mb.get("numero_impresso"))

    # 2) numeração da montagem: inventada, duplicada, decrescente
    vistos: dict[int, str] = {}
    ultimo_numero: Optional[int] = None
    for bloco in (missa.blocos or []):
        num = getattr(bloco, "numero_folheto", None)
        titulo = (bloco.titulo or "")[:60]
        if num is None:
            continue
        t = _norm_busca(bloco.titulo or "")
        # inventado: o mapa conhece o título mas não o numera
        if t in numeros_mapa and num not in (numeros_mapa[t] or []):
            divs.append({"severidade": "critica", "tipo": "bloco", "local": titulo,
                         "detalhe": f"número {num} inventado: o mapa não numera este bloco"})
        elif t not in numeros_mapa:
            divs.append({"severidade": "critica", "tipo": "bloco", "local": titulo,
                         "detalhe": f"número {num} sem bloco correspondente no mapa (apêndice/rubrica numerada?)"})
        if num in vistos:
            divs.append({"severidade": "critica", "tipo": "bloco",
                         "local": f"{vistos[num]} e {titulo}",
                         "detalhe": f"número {num} repetido: o folheto não duplica numeração"})
        else:
            vistos[num] = titulo
        if ultimo_numero is not None and num <= ultimo_numero:
            divs.append({"severidade": "critica", "tipo": "bloco", "local": titulo,
                         "detalhe": f"número {num} regride (anterior {ultimo_numero}): ordem de numeração quebrada"})
        ultimo_numero = num

    # 3) bloco numerado no mapa ausente na montagem (omissão de conteúdo numerado)
    titulos_montagem = {_norm_busca(getattr(b, "titulo", "") or "") for b in (missa.blocos or [])}
    for mb in mapa.get("blocos") or []:
        num = mb.get("numero_impresso")
        if num is None:
            continue
        t = _norm_busca(mb.get("titulo") or "")
        if t and t not in titulos_montagem:
            divs.append({"severidade": "critica", "tipo": "bloco",
                         "local": (mb.get("titulo") or "")[:60],
                         "detalhe": f"bloco numerado {num} no mapa, ausente na montagem"})
    return divs


def checar_estrutural_vs_mapa(missa: Missa, mapa: dict) -> list[dict]:
    """Divergências estruturais determinísticas entre montagem e mapa."""
    if not mapa:
        return []
    divs: list[dict] = []
    divs.extend(checar_numeracao_vs_mapa(missa, mapa))
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
            marca = (rep.get("marca") or "").lower()
            # Repetição ESTRUTURAL de refrão ("Refrão + N estrofes") está
            # representada guardando o refrão UMA única vez no campo `refrao`
            # (contrato: INSTR_CONF manda ignorar essa repetição visual).
            # Só repetições inline reais ("//: … ://", "2x") exigem linha
            # duplicada DENTRO de alguma estrofe.
            if ("refrão" in marca or "refrao" in marca) and getattr(b, "refrao", None):
                continue
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


def checar_cobertura_palavra_a_palavra(texto_limpo: str, missa: Missa) -> list[dict]:
    """Gate determinístico de omissões: texto da montagem contra PDF Celular.

    A comparação opera em tokens normalizados e preserva a tolerância mínima
    para artefatos conhecidos da extração de PDF. Qualquer achado continua no
    laço de correção; não há aprovação por amostragem ou por aparência visual.
    """
    try:
        from app.services.auditor_missa import conferir_cobertura_liturgica

        severidades = {"CRÍTICA": "critica", "ALTA": "alta", "MÉDIA": "media", "BAIXA": "baixa"}
        return [
            {
                "severidade": severidades.get(achado.severidade, "critica"),
                "escopo": "conteudo_liturgico",
                "local": achado.bloco_titulo or "Missa (geral)",
                "regra": achado.regra,
                "detalhe": achado.detalhe,
            }
            for achado in conferir_cobertura_liturgica(texto_limpo, missa)
        ]
    except Exception as e:  # noqa: BLE001
        logger.warning("checagem de cobertura falhou (%s) — publicação bloqueada", str(e)[:160])
        raise ConferenciaIndisponivel("não foi possível auditar palavra a palavra contra o PDF") from e


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

SYSTEM_CONF_CELEBRANTE = (
    "Você é um segundo conferente independente de fidelidade litúrgica. O PDF "
    "anexado é a versão oficial CELEBRANTE; compare-o com a MONTAGEM JSON sem "
    "reconstruí-la e sem avaliar qualquer escolha editorial."
)
INSTR_CONF_CELEBRANTE = (
    "O PDF anexado é a versão CELEBRANTE, usada SOMENTE como conferência secundária. "
    "Confira exclusivamente: falas do presidente (P), rubricas, postura e a Oração "
    "Eucarística, incluindo título e prefácio. Não extraia nem reordene a missa a "
    "partir dele; não avalie cantos, colunas, diagramação, paginação, cores, fontes, "
    "imagens ou outros elementos editoriais.\n"
    "Aponte apenas divergências reais de conteúdo/hierarquia no JSON. "
    'Responda SOMENTE JSON: {"divergencias":[{"severidade":"critica|baixa",'
    '"escopo":"conteudo_liturgico|hierarquia_liturgica","local":"onde",'
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


def conferir_celebrante(pdf_bytes: bytes, missa: Missa) -> list[dict]:
    """Crítica secundária focada no que a versão Celebrante esclarece melhor."""
    try:
        user = INSTR_CONF_CELEBRANTE + "\n\n=== MONTAGEM (JSON) ===\n" + _montagem_json(missa)
        data = _extrair_json(_run_coro(_gerar(
            "conferente_celebrante", SYSTEM_CONF_CELEBRANTE, user, pdf_bytes
        )))
        divergencias = data.get("divergencias")
        if not isinstance(divergencias, list):
            raise ValueError("resposta do conferente Celebrante sem lista de divergências")
        return divergencias
    except Exception as e:  # noqa: BLE001
        logger.warning("conferente Celebrante falhou (%s) — publicação bloqueada", str(e)[:160])
        raise ConferenciaIndisponivel("não foi possível executar a conferência secundária Celebrante") from e


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
    _sincronizar_numero_folheto(nova, mapa)
    return nova


def montar_com_conferencia(pdf_bytes: bytes, texto_limpo: str,
                           pdf_celebrante: bytes | None = None,
                           data_hint: Optional[str] = None) -> tuple[Missa, dict]:
    """Orquestra os passos 3–6. Retorna (missa, meta).

    meta = {conferida:bool, iteracoes:int, divergencias_restantes:[...], mapa:{...}, contrato:{...}}
    RAISE se a montagem multimodal falhar (passo 4) — o chamador agenda retry/alerta;
    NUNCA cai para texto puro aqui.
    """
    if not pdf_celebrante:
        raise ConferenciaIndisponivel(
            "PDF oficial versão Celebrante ausente; não há conferência secundária para publicar"
        )
    mapa = gerar_mapa(pdf_bytes)                                   # passo 3
    missa = montar_com_mapa(pdf_bytes, texto_limpo, mapa, data_hint)  # passo 4 (+5 determ.)

    iteracoes = 0
    divergencias: list[dict] = []
    for i in range(MAX_ITER_CONFERENCIA):
        estruturais = checar_estrutural_vs_mapa(missa, mapa)      # passo 5 (vs mapa)
        textuais = checar_texto_liturgico_vs_fonte(texto_limpo, missa)
        cobertura = checar_cobertura_palavra_a_palavra(texto_limpo, missa)
        visuais = conferir(pdf_bytes, missa)                      # passo 6 (Celular)
        celebrante = conferir_celebrante(pdf_celebrante, missa)  # segunda crítica independente
        divergencias = estruturais + textuais + cobertura + visuais + celebrante
        # O conferente recebe a instrução de devolver somente divergências litúrgicas.
        # Por isso nenhuma delas é "aceitável": conteúdo/hierarquia só convergem quando
        # a lista fica vazia. Elementos editoriais não entram nessa lista.
        if not divergencias:
            _sincronizar_numero_folheto(missa, mapa)
            logger.info("conferência convergiu em %d iteração(ões)", i)
            return missa, {"conferida": True, "iteracoes": i,
                           "divergencias_restantes": divergencias, "mapa": mapa,
                           "contrato": _contrato_gauntlet(),
                           "fontes": {"principal": "celular", "secundaria": "celebrante"}}
        iteracoes = i + 1
        logger.info("iteração %d: %d divergência(s) litúrgica(s) — corrigindo",
                    iteracoes, len(divergencias))
        try:
            # corrige TODAS as divergências (críticas gatilham o laço; baixas pegam carona)
            missa = _corrigir(pdf_bytes, texto_limpo, mapa, missa, divergencias, data_hint)
        except Exception:
            logger.exception("correção da iteração %d falhou — encerra laço", iteracoes)
            break
    # Não convergiu — a montagem retida para revisão humana também sai com a
    # numeração fiel ao mapa (defesa em profundidade).
    _sincronizar_numero_folheto(missa, mapa)
    return missa, {"conferida": False, "iteracoes": iteracoes,
                   "divergencias_restantes": divergencias, "mapa": mapa,
                   "contrato": _contrato_gauntlet(),
                   "fontes": {"principal": "celular", "secundaria": "celebrante"}}
