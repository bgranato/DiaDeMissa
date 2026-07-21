"""Estruturação do folheto via LLM (etapa 4 da arquitetura).

Substitui o regex de `structure.estruturar` por uma chamada a um LLM com schema
rígido. Mantém a etapa de validação Pydantic com reprocessamento (etapa 5) e cai
de volta no regex se o LLM falhar ou não estiver configurado — assim o pipeline
nunca quebra por causa do LLM.

Uso:
    from app.pipeline.structure_llm import estruturar_via_llm
    missa = estruturar_via_llm(texto_limpo)
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Optional

from pydantic import ValidationError

from app.schema.missa import (
    Missa, Secao, Canto, Leitura, Salmo, Aclamacao, Antifona, Oracao, Dialogo,
)
from app.llm.base import LLMClient
from app.llm.prompts import (
    SYSTEM_PROMPT, build_user_prompt, build_user_prompt_mm, build_correcao_prompt,
)

logger = logging.getLogger(__name__)

# Marcador de fallback gravado em missa.observacoes quando a montagem NÃO veio do
# caminho preferido (multimodal). persist_missa lê isso: fallback=regex → pendente_revisao.
MARCA_FALLBACK = "[pipeline] fallback="


def _marcar_fallback(missa, tipo: str) -> None:
    """Prepende '[pipeline] fallback=<tipo>' em observacoes (não sobrescreve um
    marcador já presente — o mais específico/pior, 'regex', vence)."""
    try:
        obs = missa.observacoes or ""
        if MARCA_FALLBACK in obs:
            return
        missa.observacoes = f"{MARCA_FALLBACK}{tipo}" + (f" · {obs}" if obs else "")
    except Exception:
        pass


_TIPO_PARA_CLASSE = {
    "secao": Secao,
    "canto": Canto,
    "leitura": Leitura,
    "salmo": Salmo,
    "aclamacao": Aclamacao,
    "antifona": Antifona,
    "oracao": Oracao,
    "dialogo": Dialogo,
}


def _limpar_cercas(texto: str) -> str:
    """Remove ```json ... ``` caso o modelo desobedeça e devolva markdown."""
    t = texto.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n", "", t)
        t = re.sub(r"\n```$", "", t).strip()
    return t


def _norm_busca(s: str) -> str:
    """Normaliza para casamento robusto: minúsculas, só letras/números/espaço."""
    s = re.sub(r"[^0-9a-zà-úãõâêôçáéíóú ]", "", (s or "").lower())
    return re.sub(r"\s+", " ", s).strip()


_MOMENTO_ORACAO = _norm_busca("Momento de silêncio para oração pessoal")


def _dedup_momento_silencio(missa: Missa) -> None:
    """Garante que a rubrica 'Momento de silêncio para oração pessoal' apareça como
    bloco standalone UMA única vez (mantém o primeiro). Determinístico — o LLM às
    vezes a duplica (antes e depois da Antífona da Comunhão)."""
    try:
        visto = False
        novos = []
        for b in (missa.blocos or []):
            if _norm_busca(getattr(b, "titulo", "") or "") == _MOMENTO_ORACAO:
                if visto:
                    continue
                visto = True
            novos.append(b)
        missa.blocos = novos
    except Exception:
        pass


def _tokens_repeticao(src: str):
    """Quebra um trecho de estrofe em tokens ('verse'|'repeat', texto), tratando o
    marcador de repetição do folheto "//: TEXTO ://" (ou "//: TEXTO" no fim)."""
    parts, pos = [], 0
    for m in re.finditer(r"//:\s*(.+?)\s*://", src):
        parts.append(("text", src[pos:m.start()])); parts.append(("repeat", m.group(1))); pos = m.end()
    tail = src[pos:]
    m2 = re.search(r"//:\s*(.+?)\s*$", tail)
    if m2:
        parts.append(("text", tail[:m2.start()])); parts.append(("repeat", m2.group(1)))
    else:
        parts.append(("text", tail))
    out = []
    for typ, txt in parts:
        if typ == "repeat":
            out.append(("repeat", txt.strip()))
        else:
            for v in txt.split("/"):
                v = v.strip()
                if v:
                    out.append(("verse", v))
    return out


_FIM_CANTO = re.compile(r"LEITURAS DA SEMANA|EDITORA NOSSA|PORTAL DA ARQUID|COM APROVA", re.I)


def _inserir_repeticoes_estrofes(missa: Missa, texto_limpo: str) -> None:
    """Reinsere, de forma DETERMINÍSTICA, as repetições "//: … ://" que o folheto
    imprime dentro das estrofes dos cantos (ex.: "Tantas graças…" no Canto Final).
    SEGURO: só altera uma estrofe quando a contagem de versos do texto-fonte bate
    com a da montagem — senão deixa o que o LLM produziu."""
    if "//:" not in texto_limpo:
        return
    src_flat = re.sub(r"\s+", " ", texto_limpo)
    for b in missa.blocos:
        if getattr(b, "tipo", None) != "canto":
            continue
        estrofes = getattr(b, "estrofes", None) or []
        if not estrofes:
            continue
        # posições da 1ª linha de cada estrofe no source achatado
        starts = []
        for est in estrofes:
            key = re.sub(r"\s+", " ", (est[0] if est else "")).strip()[:30]
            starts.append(src_flat.find(key) if key else -1)
        novas = list(estrofes)
        for i, est in enumerate(estrofes):
            if starts[i] < 0:
                continue
            ini = starts[i]
            proximos = [s for s in starts[i + 1:] if s > ini]
            fim = min(proximos) if proximos else None
            if fim is None:
                mfim = _FIM_CANTO.search(src_flat, ini)
                fim = mfim.start() if mfim else min(len(src_flat), ini + 800)
            toks = _tokens_repeticao(src_flat[ini:fim])
            if not any(t == "repeat" for t, _ in toks):
                continue
            nverse = sum(1 for t, _ in toks if t == "verse")
            if nverse != len(est):
                continue  # estrutura não casa → não mexe (seguro)
            merged, mi = [], 0
            for typ, txt in toks:
                if typ == "repeat":
                    merged.append(txt)
                else:
                    merged.append(est[mi]); mi += 1
            novas[i] = merged
        b.estrofes = novas


def _limpar_numero_estrofe_orfao(missa: Missa) -> None:
    """Remove o número da estrofe SEGUINTE grudado no fim do último verso da anterior
    ("…obrigado, Senhor e nosso Deus. 2." → "…nosso Deus."). Determinístico."""
    try:
        for b in missa.blocos or []:
            if getattr(b, "tipo", None) != "canto":
                continue
            for est in (getattr(b, "estrofes", None) or []):
                if isinstance(est, list) and est:
                    est[-1] = re.sub(r"\s+\d{1,2}\.\s*$", "", est[-1]).rstrip()
    except Exception:
        pass


def _corrigir_posicao_refrao(missa: Missa, texto_limpo: str) -> None:
    """Calcula `posicao_refrao_apos` dos cantos de forma DETERMINÍSTICA, pelo texto.

    Não depende do LLM acertar: olha, no texto-fonte do folheto, quantas estrofes
    aparecem ANTES do refrão e usa essa contagem. Vale para TODOS os folhetos.
    (O Salmo Responsorial não usa este campo — refrão sempre no topo.)
    """
    texto_n = _norm_busca(texto_limpo)
    for b in missa.blocos:
        if getattr(b, "tipo", None) != "canto":
            continue
        refrao = getattr(b, "refrao", None) or []
        estrofes = getattr(b, "estrofes", None) or []
        if not refrao or not estrofes:
            continue
        ref_key = _norm_busca(refrao[0])[:30]
        if not ref_key:
            continue
        idx_ref = texto_n.find(ref_key)
        if idx_ref < 0:
            continue
        # Conta estrofes ANTES do refrão usando, para CADA estrofe, a ocorrência
        # MAIS PRÓXIMA do refrão (a que pertence a este canto). Evita falso positivo
        # quando o texto da estrofe se repete em outro ponto do folheto — ex.: Canto
        # de Comunhão que reusa os versos do Salmo Responsorial, impressos antes.
        antes = 0
        for est in estrofes:
            if not est:
                continue
            est_key = _norm_busca(est[0])[:30]
            if len(est_key) < 6:
                continue
            ocorr = []
            i = texto_n.find(est_key)
            while i >= 0:
                ocorr.append(i)
                i = texto_n.find(est_key, i + 1)
            if not ocorr:
                continue
            mais_perto = min(ocorr, key=lambda p: abs(p - idx_ref))
            if mais_perto < idx_ref:
                antes += 1
        b.posicao_refrao_apos = antes


def _coagir_nulos(b: dict) -> dict:
    """Normaliza nulos que o LLM às vezes emite em campos obrigatórios.

    O modelo ocasionalmente manda `null` onde o schema exige lista ou string
    (ex.: Canto.refrao=None, Aclamacao.referencia=None) — o que reprovava o bloco
    e derrubava tudo no fallback regex. Aqui convertemos None → vazio do tipo certo,
    de forma defensiva, sem depender do LLM acertar.
    """
    for k in ("refrao", "estrofes", "versiculos", "turnos"):
        if k in b and b[k] is None:
            b[k] = []
    req_str_por_tipo = {
        "salmo": ("referencia",),
        "aclamacao": ("referencia", "versiculo"),
        "leitura": ("referencia",),
        "antifona": ("texto",),
        "oracao": ("texto",),
    }
    for k in req_str_por_tipo.get(b.get("tipo"), ()):
        if b.get(k) is None:
            b[k] = ""
    return b


def _montar_missa(dados: dict) -> Missa:
    """Constrói o objeto Missa validado a partir do dict do LLM.

    Faz o parse discriminado por `tipo` (a Union do schema não tem discriminador
    declarado, então mapeamos explicitamente) e deixa o Pydantic validar cada
    bloco — disparando os validadores de artefato (validar_texto_limpo).
    """
    brutos = dados.get("blocos", [])
    blocos = []
    for b in brutos:
        tipo = b.get("tipo")
        classe = _TIPO_PARA_CLASSE.get(tipo)
        if classe is None:
            raise ValueError(f"Bloco com tipo desconhecido: {tipo!r}")
        blocos.append(classe(**_coagir_nulos(b)))

    payload = dict(dados)
    payload["blocos"] = blocos
    return Missa(**payload)


async def _chamar_llm(client: LLMClient, texto_limpo: str, data_hint: Optional[str]) -> Missa:
    user = build_user_prompt(texto_limpo, data_hint)
    bruto = _limpar_cercas(await client.gerar(SYSTEM_PROMPT, user))

    # Tentativa 1
    try:
        return _montar_missa(json.loads(bruto))
    except (json.JSONDecodeError, ValidationError, ValueError) as e:
        erro_msg = str(e)
        logger.warning("LLM: 1ª validação falhou (%s). Reprocessando...", erro_msg[:200])

    # Tentativa 2: devolve o erro pro modelo corrigir (etapa 5 da arquitetura)
    correcao = build_correcao_prompt(bruto, erro_msg)
    bruto2 = _limpar_cercas(await client.gerar(SYSTEM_PROMPT, correcao))
    return _montar_missa(json.loads(bruto2))


async def _chamar_llm_mm(client: LLMClient, pdf_bytes: bytes, texto_limpo: str, data_hint: Optional[str]) -> Missa:
    """Igual a _chamar_llm, mas envia o PDF (fonte da verdade) junto com o texto."""
    user = build_user_prompt_mm(texto_limpo, data_hint)
    bruto = _limpar_cercas(await client.gerar(SYSTEM_PROMPT, user, pdf_bytes=pdf_bytes))
    try:
        return _montar_missa(json.loads(bruto))
    except (json.JSONDecodeError, ValidationError, ValueError) as e:
        erro_msg = str(e)
        logger.warning("LLM-MM: 1ª validação falhou (%s). Reprocessando...", erro_msg[:200])
    correcao = build_correcao_prompt(bruto, erro_msg)
    bruto2 = _limpar_cercas(await client.gerar(SYSTEM_PROMPT, correcao, pdf_bytes=pdf_bytes))
    return _montar_missa(json.loads(bruto2))


def estruturar_via_llm_mm(
    pdf_bytes: bytes,
    texto_limpo: str,
    data_hint: Optional[str] = None,
    client: Optional[LLMClient] = None,
) -> Missa:
    """Montagem MULTIMODAL: o LLM lê o PDF direto (fonte da verdade) + texto auxílio.

    Elimina a classe de erros de extração/regex na origem. Em qualquer falha, cai
    no caminho de texto (`estruturar_via_llm`), que por sua vez cai no regex.
    """
    if client is None:
        from app.llm.factory import get_llm_client
        client = get_llm_client()
    try:
        missa = asyncio.run(_chamar_llm_mm(client, pdf_bytes, texto_limpo, data_hint))
        _corrigir_posicao_refrao(missa, texto_limpo)
        _inserir_repeticoes_estrofes(missa, texto_limpo)
        _limpar_numero_estrofe_orfao(missa)
        _dedup_momento_silencio(missa)
        return missa
    except Exception as e:
        logger.exception("LLM-MM falhou — fallback para montagem por texto (%s)", str(e)[:200])
        missa = estruturar_via_llm(texto_limpo, data_hint, client)
        # Se o caminho de texto não caiu em regex, registra que foi fallback=texto.
        _marcar_fallback(missa, "texto")
        return missa


def estruturar_via_llm(
    texto_limpo: str,
    data_hint: Optional[str] = None,
    client: Optional[LLMClient] = None,
) -> Missa:
    """Estrutura o folheto via LLM com validação + 1 reprocessamento.

    Em qualquer falha (sem API key, timeout, JSON inválido 2x), cai no regex
    `structure.estruturar` para não derrubar o pipeline diário.
    """
    if client is None:
        from app.llm.factory import get_llm_client
        client = get_llm_client()

    try:
        missa = asyncio.run(_chamar_llm(client, texto_limpo, data_hint))
        # Correção determinística (não depende do LLM): posição do refrão pelo texto.
        _corrigir_posicao_refrao(missa, texto_limpo)
        _inserir_repeticoes_estrofes(missa, texto_limpo)
        _limpar_numero_estrofe_orfao(missa)
        _dedup_momento_silencio(missa)
        return missa
    except Exception as e:
        logger.exception("LLM indisponível/falhou — fallback para regex (%s)", str(e)[:200])
        from app.pipeline.structure import estruturar
        missa = estruturar(texto_limpo)
        _marcar_fallback(missa, "regex")
        return missa
