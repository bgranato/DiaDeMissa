"""Scraper da liturgia diária via Canção Nova (republica textos oficiais da CNBB).

Fonte: https://liturgia.cancaonova.com/pb/?sDia=DD&sMes=MM&sAno=AAAA

Estrutura extraída (cada dia):
    - titulo: "Quinta-feira da 6ª semana do Tempo Pascal"
    - cor_liturgica: "Branco" / "Verde" / "Violeta" / "Vermelho"
    - tempo_liturgico: derivado do título
    - 1ª Leitura: {referencia, texto}
    - Salmo: {referencia, refrao, estrofes (texto unificado)}
    - 2ª Leitura: {referencia, texto}  (só em domingos/solenidades)
    - Aclamação: {referencia, texto}
    - Evangelho: {referencia, texto}

CloudFront na frente do site cacheia agressivamente — usamos Cache-Control: no-cache
no request pra forçar miss e pegar o dia certo.

Atribuição: textos litúrgicos © CNBB (Conferência Nacional dos Bispos do Brasil).
"""
from __future__ import annotations

import logging
import re
import time
from datetime import date as date_type
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://liturgia.cancaonova.com/pb/"
USER_AGENT = "DiaDeMissa-App/1.0 (admin@diademissa.app)"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

_last_request_ts = 0.0


def _respeitar_rate_limit():
    global _last_request_ts
    agora = time.time()
    delta = agora - _last_request_ts
    if delta < 0.8:
        time.sleep(0.8 - delta)
    _last_request_ts = time.time()


_RE_INTRO_LEITURA_INICIO = re.compile(r"^\s*Leitura\s+d(?:o|os|a|as)\s+", re.IGNORECASE)
_RE_INTRO_LEITURA_PREFIXO = re.compile(r"^\s*Leitura\s+d(?:o|os|a|as)\s+[^.]{0,90}\.\s*", re.IGNORECASE)


def _limpar_intro_leitura(t: str) -> str:
    """Trata o cabeçalho 'Leitura do/da <livro>...' que às vezes vem COLADO ao corpo.

    - Colado (intro terminada em ponto + corpo no mesmo parágrafo): remove só o
      prefixo da intro e preserva o corpo da leitura.
    - Isolado (só o cabeçalho, com ou sem ponto): retorna '' (o chamador descarta).
    - Parágrafo que não começa com 'Leitura d...': retorna inalterado.
    """
    if not _RE_INTRO_LEITURA_INICIO.match(t):
        return t
    m = _RE_INTRO_LEITURA_PREFIXO.match(t)
    if m:
        return t[m.end():].strip()
    return ""  # cabeçalho isolado sem ponto → descarta


def _texto_estruturado(div) -> str:
    """Converte um <div id="liturgia-N"> em texto limpo, removendo cabeçalhos redundantes
    (que já aparecem no header do bloco da UI) e compactando espaços.
    """
    if div is None:
        return ""

    # Padrões a IGNORAR (já estão no título/referência do bloco — duplicação visual)
    PADROES_IGNORAR = [
        re.compile(r"^Primeira\s+Leitura\s*\(.*\)\s*$", re.IGNORECASE),
        re.compile(r"^Segunda\s+Leitura\s*\(.*\)\s*$", re.IGNORECASE),
        re.compile(r"^Respons[óo]rio\s+.*$", re.IGNORECASE),
        re.compile(r"^Evangelho\s*\(.*\)\s*$", re.IGNORECASE),
        re.compile(r"^Aleluia,?\s+Aleluia,?\s+Aleluia\.?\s*$", re.IGNORECASE),
        re.compile(r"^Leitura\s+do\s+Santo\s+Evangelho\s+.*$", re.IGNORECASE),
    ]

    paragrafos = []
    for p in div.find_all("p"):
        t = p.get_text(" ", strip=True)
        t = re.sub(r"\s+", " ", t)
        if not t:
            continue
        # A intro "Leitura do Livro..." às vezes vem COLADA ao corpo no mesmo <p>
        # (bug observado em 16/06). Remove só o prefixo e preserva o corpo; se sobrar
        # vazio, era só o cabeçalho isolado e é descartado.
        t = _limpar_intro_leitura(t)
        if not t:
            continue
        # Pula outros cabeçalhos redundantes
        if any(pat.match(t) for pat in PADROES_IGNORAR):
            continue
        paragrafos.append(t)

    # Junta com quebra simples (\n) em vez de dupla — reduz espaço vertical mantendo separação
    return "\n".join(paragrafos)


def _extrair_referencia(soup, num_liturgia: int) -> Optional[str]:
    """Pega a referência bíblica da aba (a#lit-N → div.referencia)."""
    a = soup.select_one(f"a#lit-{num_liturgia}")
    if not a:
        return None
    ref = a.select_one("div.referencia")
    if not ref:
        return None
    return re.sub(r"\s+", " ", ref.get_text(strip=True))


_calendario_cache: dict[tuple[int, int], dict[int, str]] = {}


def _obter_calendario_mes(ano: int, mes: int) -> dict[int, str]:
    """Retorna mapeamento {dia → URL canônica do slug} a partir do calendário do mês.

    CloudFront ignora query string, então usar `?sDia=DD&sMes=MM&sAno=AAAA` direto
    retorna sempre o dia atual. Pra contornar, lemos o calendário (#wp-calendar) que
    expõe a URL canônica de cada dia (via slug único).
    """
    if (ano, mes) in _calendario_cache:
        return _calendario_cache[(ano, mes)]

    _respeitar_rate_limit()
    url = f"{BASE_URL}?sMes={mes:02d}&sAno={ano}"
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=15.0, follow_redirects=True)
        if resp.status_code != 200:
            return {}
        html = resp.text
    except Exception:
        logger.exception("Falha buscando calendário %d/%d", mes, ano)
        return {}

    # Extrai links do calendário: <a href="...liturgia/SLUG/?sDia=DD&sMes=MM&sAno=YYYY">
    padrao = re.compile(
        rf'<a\s+href="(https://liturgia\.cancaonova\.com/pb/liturgia/[^"]+/)\?sDia=(\d+)&sMes={mes:02d}&sAno={ano}"',
        re.IGNORECASE,
    )
    cal: dict[int, str] = {}
    for m in padrao.finditer(html):
        slug_url = m.group(1)
        dia = int(m.group(2))
        cal[dia] = slug_url

    if cal:
        _calendario_cache[(ano, mes)] = cal
    return cal


def buscar_liturgia(data: date_type) -> Optional[dict]:
    """Busca a liturgia oficial CNBB pra uma data específica.

    Estratégia: pega URL canônica via calendário do mês (slug), depois fetch direto.
    Cada slug é único — CloudFront cacheia por slug, então a data certa volta.

    Returns:
        dict com chaves: titulo, cor_liturgica, tempo_liturgico,
            leitura_1, salmo, leitura_2 (opc), aclamacao, evangelho
        ou None se falhar.
    """
    # 1) Resolve slug canônico via calendário
    cal = _obter_calendario_mes(data.year, data.month)
    slug_url = cal.get(data.day)
    if not slug_url:
        logger.warning("Slug canônico não encontrado pra %s", data)
        return None

    _respeitar_rate_limit()
    try:
        resp = httpx.get(slug_url, headers=HEADERS, timeout=15.0, follow_redirects=True)
        if resp.status_code != 200:
            logger.warning("Canção Nova retornou status %s para %s", resp.status_code, data)
            return None
        html = resp.text
    except Exception:
        logger.exception("Falha buscando liturgia de %s", data)
        return None

    soup = BeautifulSoup(html, "html.parser")
    # Sanity check via #dia-calendar / #mes-calendar / #ano-calendar
    dia_cal = soup.select_one("#dia-calendar")
    mes_cal = soup.select_one("#mes-calendar")
    ano_cal = soup.select_one("#ano-calendar")
    if dia_cal and mes_cal and ano_cal:
        try:
            d, m, a = int(dia_cal.get_text(strip=True)), int(mes_cal.get_text(strip=True)), int(ano_cal.get_text(strip=True))
            if (d, m, a) != (data.day, data.month, data.year):
                logger.warning("Canção Nova retornou data %d/%d/%d em vez de %s (slug ainda cacheado?)", d, m, a, data)
                return None
        except (ValueError, TypeError):
            pass

    # Título e cor litúrgica
    h1 = soup.select_one("h1.entry-title")
    titulo = h1.get_text(" ", strip=True) if h1 else None

    cor_span = soup.select_one("span.cor-liturgica")
    cor_liturgica = None
    if cor_span:
        m = re.search(r"Cor\s+Lit[uú]rgica:\s*(\w+)", cor_span.get_text(strip=True), re.IGNORECASE)
        cor_liturgica = m.group(1) if m else None

    # Deriva tempo litúrgico do título
    tempo_liturgico = None
    if titulo:
        for tempo in ("Páscoa", "Pascal", "Advento", "Natal", "Quaresma", "Tempo Comum", "Comum"):
            if tempo.lower() in titulo.lower():
                tempo_liturgico = tempo
                break

    # Conteúdos das abas
    leitura_1_div = soup.select_one("div#liturgia-1")
    salmo_div = soup.select_one("div#liturgia-2")
    leitura_2_div = soup.select_one("div#liturgia-3")
    evangelho_div = soup.select_one("div#liturgia-4")

    if not (leitura_1_div and salmo_div and evangelho_div):
        logger.warning("Estrutura HTML inesperada para %s — campos essenciais ausentes", data)
        return None

    leitura_1_texto = _texto_estruturado(leitura_1_div)
    salmo_texto = _texto_estruturado(salmo_div)
    leitura_2_texto = _texto_estruturado(leitura_2_div) if leitura_2_div else None
    evangelho_completo = _texto_estruturado(evangelho_div)

    # A Canção Nova embute no bloco do Evangelho:
    # 1. Aclamação no topo (Aleluia + versículo) — separamos pro bloco próprio
    # 2. "-Glória a vós, Senhor." (resposta da assembleia ANTES do Evangelho)
    # 3. "Proclamação do Evangelho..." (rubrica do padre)
    # 4. "Palavra da Salvação." (conclusão) + "Louvor a vós, ó Cristo." (resposta)
    # Removemos tudo que NÃO é o texto bíblico em si.
    aclamacao_texto = None
    evangelho_texto = evangelho_completo

    # Tenta separar Aclamação por "Proclamação do Evangelho"
    m_split = re.search(r"(Proclama[çc][ãa]o\s+do\s+Evangelho[^\n]*)", evangelho_completo, re.IGNORECASE)
    if m_split:
        aclamacao_texto = evangelho_completo[: m_split.start()].strip()
        evangelho_texto = evangelho_completo[m_split.start():].strip()
        evangelho_texto = re.sub(r"^Proclama[çc][ãa]o\s+do\s+Evangelho[^\n]*\n*", "", evangelho_texto, flags=re.IGNORECASE)
    else:
        # Sem "Proclamação..." — tenta separar Aclamação pelo padrão "Glória a vós, Senhor"
        m_gloria = re.search(r"[—–-]?\s*Gl[óo]ria\s+a\s+v[óo]s,?\s+Senhor[\.\s]*", evangelho_completo, re.IGNORECASE)
        if m_gloria:
            aclamacao_texto = evangelho_completo[: m_gloria.start()].strip()
            evangelho_texto = evangelho_completo[m_gloria.end():].strip()

    # Limpeza final do texto do Evangelho — remove respostas/rubricas remanescentes
    evangelho_texto = re.sub(
        r"^[—–-]?\s*Gl[óo]ria\s+a\s+v[óo]s,?\s+Senhor[\.\s]*\n*", "",
        evangelho_texto, flags=re.IGNORECASE,
    )
    # Remove a conclusão e resposta finais
    evangelho_texto = re.sub(
        r"\n*[—–-]?\s*Palavra\s+da\s+Salva[çc][ãa]o[\.\s]*(\n*[—–-]?\s*Louvor\s+a\s+v[óo]s,?\s+[óo]\s+Cristo[\.\s]*)?$",
        "", evangelho_texto, flags=re.IGNORECASE,
    ).strip()

    return {
        "data": data.isoformat(),
        "titulo": titulo,
        "cor_liturgica": cor_liturgica,
        "tempo_liturgico": tempo_liturgico,
        "leitura_1": {
            "referencia": _extrair_referencia(soup, 1),
            "texto": leitura_1_texto,
        },
        "salmo": {
            "referencia": _extrair_referencia(soup, 2),
            "texto": salmo_texto,
        },
        "leitura_2": ({
            "referencia": _extrair_referencia(soup, 3),
            "texto": leitura_2_texto,
        } if leitura_2_texto else None),
        "aclamacao": {
            "referencia": _extrair_referencia(soup, 4),
            "texto": aclamacao_texto,
        } if aclamacao_texto else None,
        "evangelho": {
            "referencia": _extrair_referencia(soup, 4),
            "texto": evangelho_texto,
        },
        "fonte_url": slug_url,
    }
