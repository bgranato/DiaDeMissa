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
    SYSTEM_PROMPT, build_user_prompt, build_correcao_prompt,
)

logger = logging.getLogger(__name__)

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
        antes = 0
        for est in estrofes:
            if not est:
                continue
            est_key = _norm_busca(est[0])[:30]
            if not est_key:
                continue
            idx_est = texto_n.find(est_key)
            if 0 <= idx_est < idx_ref:
                antes += 1
        b.posicao_refrao_apos = antes if antes > 0 else 0


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
        return missa
    except Exception as e:
        logger.exception("LLM indisponível/falhou — fallback para regex (%s)", str(e)[:200])
        from app.pipeline.structure import estruturar
        missa = estruturar(texto_limpo)
        try:
            missa.observacoes = (missa.observacoes or "")
        except Exception:
            pass
        return missa
