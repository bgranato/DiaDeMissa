"""Verificador LEXICAL determinístico (sem LLM) — camada entre a montagem e o gate.

Ideia: toda palavra do texto litúrgico da montagem DEVE existir no vocabulário do
texto-fonte do folheto (o mesmo `texto_limpo` que alimenta o LLM). Uma palavra que
NÃO existe na fonte é forte suspeita de typo do modelo (caso real: "devis" no lugar
de "deveis", missa 2026-06-14).

Barato, determinístico e sem falso-negativo por variância de LLM. Cuidados contra
FALSO-POSITIVO: normalização unicode (NFC) + minúsculas + remoção de hífen/apóstrofo
iguais em ambos os lados (o PDF hifeniza palavras na quebra de linha); ignora
números, siglas de 1–2 letras e campos de metadados.

Uso:
    from app.services.verificador_lexical import verificar_lexico
    suspeitas = verificar_lexico(texto_limpo, [b.model_dump() for b in missa.blocos], missa.descricao)
"""
from __future__ import annotations

import logging
import os
import re
import unicodedata

logger = logging.getLogger(__name__)

MARCA_LEXICAL = "[lexical] palavras fora do fonte: "

# Palavra: letras (com acento) e apóstrofo/hífen internos ("todo-poderoso", "ofertar-vos").
_WORD_RE = re.compile(r"[a-zà-ÿ]+(?:[-'’][a-zà-ÿ]+)*", re.IGNORECASE)

# Campos de CONTEÚDO litúrgico a verificar (metadados ficam de fora).
_CAMPOS_TEXTO = ("introducao", "texto", "conteudo", "descricao", "conclusao", "resposta", "subtitulo", "versiculo")

# Não são typos: comuns fora do corpo do folheto ou artefatos estruturais.
_IGNORAR = {"amém", "aleluia", "hosana", "glória"}


def _key(w: str) -> str:
    """Chave de comparação: NFC, minúsculas, sem hífen/apóstrofo. NÃO remove acento
    (typo 'devis' vs 'deveis' difere por letra, não por acento)."""
    w = unicodedata.normalize("NFC", w or "").lower()
    return re.sub(r"[-'’]", "", w)


def _palavras(texto: str):
    return _WORD_RE.findall(unicodedata.normalize("NFC", texto or ""))


def vocabulario_fonte(texto_limpo: str) -> set[str]:
    """Conjunto de chaves das palavras do texto-fonte (inclui a forma juntada e as
    partes de palavras hifenizadas, para casar as duas grafias)."""
    vocab: set[str] = set()
    for w in _palavras(texto_limpo):
        k = _key(w)
        if k:
            vocab.add(k)
        for parte in re.split(r"[-'’]", w):
            pk = _key(parte)
            if pk:
                vocab.add(pk)
    return vocab


def _flat(e):
    if isinstance(e, str):
        return [e]
    if isinstance(e, (list, tuple)):
        out = []
        for x in e:
            out.extend(_flat(x))
        return out
    if isinstance(e, dict):
        return [str(e.get("texto") or "")]
    return [str(e)]


def _textos_do_bloco(bd: dict):
    """Lista (campo, texto) do conteúdo litúrgico de um bloco (dict)."""
    out = []
    for k in _CAMPOS_TEXTO:
        if bd.get(k):
            out.append((k, str(bd[k])))
    for v in bd.get("versiculos") or []:
        if isinstance(v, dict) and v.get("texto"):
            out.append(("versiculo", str(v["texto"])))
    for t in bd.get("turnos") or []:
        if isinstance(t, dict) and t.get("texto"):
            out.append(("turno", str(t["texto"])))
    for e in bd.get("estrofes") or []:
        for s in _flat(e):
            out.append(("estrofe", s))
    if bd.get("refrao"):
        for s in _flat(bd["refrao"]):
            out.append(("refrao", s))
    return out


def _conhecida(k: str, vocab: set[str]) -> bool:
    """Palavra conhecida se está no vocabulário OU se uma token da fonte (≥5 letras)
    é a palavra da montagem sem até 3 letras finais. Isso absorve a TRUNCAGEM que a
    extração do PDF faz em palavras acentuadas ("aclamações" na montagem × "aclamaçõ"
    na fonte), SEM mascarar typo por letra dropada no meio ("devis" continua flagrado,
    pois nenhuma token ≥5 é prefixo de 'devis')."""
    if k in vocab:
        return True
    for n in (1, 2, 3):
        pref = k[:-n]
        if len(pref) >= 5 and pref in vocab:
            return True
    return False


def verificar_lexico(texto_limpo: str, blocos: list[dict], descricao: str | None = None) -> list[dict]:
    """Retorna a lista de suspeitas (palavras da montagem ausentes no fonte).

    Cada suspeita: {bloco, campo, palavra, contexto}. Vazio = tudo confere.
    """
    vocab = vocabulario_fonte(texto_limpo)
    if descricao:
        # a descrição de abertura também vem do folheto — inclui no fonte por segurança
        vocab |= vocabulario_fonte(descricao)
    suspeitas: list[dict] = []
    vistos: set[str] = set()
    for bd in blocos or []:
        titulo = bd.get("titulo") or bd.get("tipo") or "?"
        for campo, texto in _textos_do_bloco(bd):
            for w in _palavras(texto):
                k = _key(w)
                if len(k) < 3:            # ignora siglas P/T/L e monossílabos
                    continue
                if k in _IGNORAR or _conhecida(k, vocab):
                    continue
                if k in vistos:
                    continue
                vistos.add(k)
                ctx = re.sub(r"\s+", " ", texto).strip()
                i = ctx.lower().find(w.lower())
                if i >= 0:
                    ctx = ctx[max(0, i - 30):i + len(w) + 30]
                suspeitas.append({"bloco": str(titulo), "campo": campo, "palavra": w, "contexto": ctx})
    return suspeitas


def modo() -> str:
    """'bloquear' (pendente_revisao) ou 'alertar' (só log/email). Default: alertar
    (medir falso-positivo antes de bloquear, conforme plano)."""
    return os.getenv("VERIFICADOR_LEXICAL_MODO", "alertar").strip().lower()


def ativo() -> bool:
    return os.getenv("USAR_VERIFICADOR_LEXICAL", "1").strip().lower() in ("1", "true", "yes", "on")


def resumo(suspeitas: list[dict]) -> str:
    """Palavras suspeitas únicas, em ordem, para gravar em observacoes/log."""
    vistas, out = set(), []
    for s in suspeitas:
        p = s.get("palavra")
        if p and p not in vistas:
            vistas.add(p); out.append(p)
    return ", ".join(out)


def enviar_alerta_lexical(data_iso: str, suspeitas: list[dict]) -> None:
    """Best-effort: e-mail para os admins com as palavras suspeitas (modo alertar)."""
    try:
        from app.core.database import SessionLocal
        from app.models.usuario import Usuario
        from app.services.email_sender import enviar_email
        db = SessionLocal()
        try:
            admins = db.query(Usuario).filter(Usuario.is_admin == True).all()  # noqa: E712
            emails = [a.email for a in admins if a.email]
        finally:
            db.close()
        if not emails:
            return
        linhas = "".join(
            f"<li><b>{s['palavra']}</b> — {s['bloco']} ({s['campo']}): …{s['contexto']}…</li>"
            for s in suspeitas
        )
        corpo = (
            f"<p>Verificador léxico encontrou {len(suspeitas)} palavra(s) na montagem da missa "
            f"<b>{data_iso}</b> que NÃO existem no texto-fonte do folheto (suspeita de typo):</p>"
            f"<ul>{linhas}</ul>"
            f"<p>Confira em Perfil → Revisão de Missas ou no PDF oficial.</p>"
        )
        for e in emails:
            enviar_email(e, f"[Dia de Missa] Verificação léxica — {data_iso}", corpo)
    except Exception:
        logger.exception("Falha ao enviar alerta léxico (não bloqueante) %s", data_iso)
