"""Scraper do catálogo oficial de paróquias e locais de culto da Arquidiocese RJ.

Fonte: https://www.arqrio.com.br/curia/paroquias.php

Estratégia:
- Pagina 1..6 lista IDs internos de paróquias.
- ajaxParoquiasRecuperarDetalhes.php?id={id} retorna fragmento HTML com:
    - Dados da paróquia (nome, endereço administrativo, telefones)
    - <ul> dos "Locais de culto" — cada <li> é uma matriz/capela individual com
      lat/lng (embutidos no onclick="exibirMapa('lat','lng', ...)"), endereço, CEP, tel.

Cada local de culto vira uma Igreja no nosso BD — é a unidade que o usuário busca.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Iterator, Optional

import httpx
from bs4 import BeautifulSoup, NavigableString

logger = logging.getLogger(__name__)

BASE_CURIA = "https://www.arqrio.com.br/curia"
USER_AGENT = "DiaDeMissa-App/1.0 (admin@diademissa.app)"
HEADERS = {"User-Agent": USER_AGENT}

_RE_RECUPERA_ID = re.compile(r"recuperaDetalhes\('panel-body\d+','(\d+)'")
_RE_MAPA = re.compile(r"exibirMapa\('(-?\d+\.\d+)','(-?\d+\.\d+)','DIVMAP(\d+)'")
_RE_LOCAL_ID = re.compile(r"id=\"DIV(?:MAP|ATI|TEMP)?(\d+)\"")
_RE_CEP = re.compile(r"(\d{5}-\d{3})")
_RE_TEL = re.compile(r"Telefones?:\s*([^<\n]+)")
_RE_EMAIL = re.compile(r"E-mail:\s*([^\s<]+)")


def _http_get(url: str, retries: int = 2) -> Optional[str]:
    for tentativa in range(retries + 1):
        try:
            r = httpx.get(url, headers=HEADERS, timeout=20.0)
            if r.status_code == 200:
                return r.text
            logger.warning("HTTP %s em %s", r.status_code, url)
        except Exception:
            logger.exception("Erro fetch %s (tentativa %d)", url, tentativa + 1)
        time.sleep(1.0)
    return None


def listar_ids_paroquias() -> list[str]:
    """Coleta os IDs de todas as paróquias (paginação 1..6)."""
    ids: list[str] = []
    for pagina in range(1, 8):  # 6 páginas + margem
        html = _http_get(f"{BASE_CURIA}/paroquias.php?pagina={pagina}")
        if not html:
            continue
        encontrados = _RE_RECUPERA_ID.findall(html)
        if not encontrados and pagina > 1:
            break  # passou da última página real
        ids.extend(encontrados)
        time.sleep(0.4)
    # Dedupe preservando ordem
    return list(dict.fromkeys(ids))


def _texto_apos(node, marker: str) -> Optional[str]:
    """Pega o texto livre que segue um marker (ex.: 'Telefones:') dentro de um nó."""
    txt = node.get_text("\n", strip=False)
    m = re.search(rf"{re.escape(marker)}\s*([^\n<]+)", txt)
    return m.group(1).strip() if m else None


def _parsear_paroquia(html: str) -> Optional[dict]:
    """Parseia o fragmento HTML do detalhe da paróquia."""
    if not html or not html.strip():
        return None
    soup = BeautifulSoup(html, "html.parser")

    # Nome da paróquia: primeiro <b>
    b = soup.find("b")
    if not b:
        return None
    nome_paroquia = b.get_text(strip=True)

    # Encontra o <p> que contém o cabeçalho da paróquia (com endereço administrativo)
    p_paroquia = b.find_parent("p")
    texto_p = p_paroquia.get_text("\n", strip=False) if p_paroquia else ""
    cep_paroquia = (_RE_CEP.search(texto_p) or [None, None])[0] if _RE_CEP.search(texto_p) else None
    tel_paroquia = _RE_TEL.search(texto_p).group(1).strip() if _RE_TEL.search(texto_p) else None
    email_paroquia = _RE_EMAIL.search(texto_p).group(1).strip() if _RE_EMAIL.search(texto_p) else None

    # Localiza o <ul> dentro do <p><b>Locais de culto</b>
    locais: list[dict] = []
    ul_locais = None
    for tag_b in soup.find_all("b"):
        if "Locais de culto" in tag_b.get_text(strip=True):
            container = tag_b.find_parent("p") or tag_b.parent
            ul_locais = container.find("ul") if container else None
            # Às vezes o <ul> está depois do <p>, irmão
            if ul_locais is None and container:
                ul_locais = container.find_next_sibling("ul")
            break

    if ul_locais is None:
        # Fallback: pega todos os <li> que parecem locais (têm exibirMapa ou endereço)
        ul_locais = soup

    for li in ul_locais.find_all("li", recursive=True):
        # Skipa <li> de clérigos (ficam num <ul> diferente; quando passamos o `ul_locais` real isso já é evitado)
        texto_li = li.get_text("\n", strip=False)
        nome_local = texto_li.split("\n", 1)[0].strip()
        # Remove sufixos de ícones
        nome_local = re.sub(r"\s+", " ", nome_local).strip()
        if not nome_local or len(nome_local) < 3:
            continue
        # Pula entradas que claramente não são igreja (clérigos, etc.)
        if re.match(r"^(Pároco|Vigário|Diácono|Exercício|Auxiliar)\b", nome_local, re.IGNORECASE):
            continue

        # Lat/lng + local_id do onclick="exibirMapa(...)" e divs DIV/DIVMAP/DIVATI
        m = _RE_MAPA.search(str(li))
        lat = float(m.group(1)) if m else None
        lng = float(m.group(2)) if m else None
        local_id = int(m.group(3)) if m else None
        # Fallback: extrai do id="DIV{N}" se exibirMapa estiver ausente (capelas sem coord)
        if local_id is None:
            m2 = _RE_LOCAL_ID.search(str(li))
            if m2:
                local_id = int(m2.group(1))

        # Endereço: tudo após o primeiro <br/> dentro do <li>
        # Procura blocos de texto que parecem endereço (Rua/Avenida/Praça)
        partes = []
        for piece in li.find_all(string=True, recursive=True):
            s = piece.strip()
            if not s:
                continue
            partes.append(s)
        # Junta e tenta extrair: endereço (linha com Rua/Av/Pç), CEP-Cidade, tel, email
        endereco = None
        cidade = None
        estado = None
        cep = None
        telefone = None
        email = None
        for s in partes:
            s_clean = re.sub(r"\s+", " ", s).strip()
            if not s_clean:
                continue
            if endereco is None and re.match(r"^(Rua|Avenida|Av\.|Praça|Pç\.|Estrada|Travessa|Largo|Alameda|Rodovia|Beco|Ladeira)\b", s_clean, re.IGNORECASE):
                endereco = s_clean
                continue
            mc = _RE_CEP.search(s_clean)
            if mc:
                cep = mc.group(1)
                # Cidade + UF: após o CEP
                resto = s_clean[mc.end():].strip(" -,")
                # Formato típico: "Rio de Janeiro, RJ" ou "Rio de Janeiro - RJ"
                mcid = re.match(r"([^,\-]+)[\s,\-]+([A-Z]{2})", resto)
                if mcid:
                    cidade = mcid.group(1).strip()
                    estado = mcid.group(2).strip()
                continue
            mt = re.match(r"Telefones?:\s*(.+)", s_clean)
            if mt:
                telefone = mt.group(1).strip()
                continue
            me = re.match(r"E-mail:\s*(\S+)", s_clean)
            if me:
                email = me.group(1).strip()
                continue

        locais.append({
            "nome": nome_local,
            "endereco": endereco,
            "cidade": cidade,
            "estado": estado,
            "cep": cep,
            "telefone": telefone or tel_paroquia,
            "site": None,
            "lat": lat,
            "lng": lng,
            "email": email or email_paroquia,
            "paroquia": nome_paroquia,
            "arqrio_local_id": local_id,
        })

    return {
        "paroquia": nome_paroquia,
        "cep_paroquia": cep_paroquia,
        "tel_paroquia": tel_paroquia,
        "email_paroquia": email_paroquia,
        "locais": locais,
    }


def buscar_detalhes_paroquia(id_paroquia: str) -> Optional[dict]:
    """Fetch + parse de uma paróquia. Retorna dict com lista de locais ou None se falhar."""
    html = _http_get(f"{BASE_CURIA}/ajaxParoquiasRecuperarDetalhes.php?id={id_paroquia}")
    if not html:
        return None
    return _parsear_paroquia(html)


_RE_DIA = re.compile(
    r"^(domingos?|segundas?[\-\s]feiras?|ter[çc]as?[\-\s]feiras?|quartas?[\-\s]feiras?|"
    r"quintas?[\-\s]feiras?|sextas?[\-\s]feiras?|s[áa]bados?|diariamente|todos\s+os\s+dias)\b",
    re.IGNORECASE,
)
_RE_HORA = re.compile(r"\b(\d{1,2}):?(\d{2})?\s*h\b", re.IGNORECASE)

_DIAS_MAP = {
    "domingo": "Dom", "domingos": "Dom",
    "segunda-feira": "Seg", "segundas-feiras": "Seg", "segunda feira": "Seg",
    "terça-feira": "Ter", "terças-feiras": "Ter", "terca-feira": "Ter", "terças-feira": "Ter",
    "quarta-feira": "Qua", "quartas-feiras": "Qua",
    "quinta-feira": "Qui", "quintas-feiras": "Qui",
    "sexta-feira": "Sex", "sextas-feiras": "Sex",
    "sábado": "Sáb", "sábados": "Sáb", "sabado": "Sáb", "sabados": "Sáb",
    "diariamente": "Diário", "todos os dias": "Diário",
}
_DIAS_ORDEM = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Diário"]


def _normalizar_horas(texto: str) -> list[str]:
    """Extrai horários no formato '7h', '7h30', etc. do texto livre."""
    horas: list[str] = []
    for m in _RE_HORA.finditer(texto):
        h = int(m.group(1))
        mins = m.group(2)
        if mins and mins != "00":
            horas.append(f"{h}h{mins}")
        else:
            horas.append(f"{h}h")
    # Dedupe preservando ordem
    return list(dict.fromkeys(horas))


def buscar_horarios_local(local_id: int) -> Optional[str]:
    """Busca horários de missa de um local via ajaxExibeAtividadesLocal.php.

    Parser robusto: extrai dia da semana + horários (formato HH:MM h), ignora descrições
    em parênteses. Retorna "Dom 7h, 10h, 18h | Seg 19h | Sáb 18h" ou None.
    """
    if not local_id:
        return None
    html = _http_get(f"{BASE_CURIA}/ajaxExibeAtividadesLocal.php?id={local_id}&div=DIVATI{local_id}")
    if not html or not html.strip():
        return None

    # Encontra o bloco "Missa" — texto entre <span>Missa</span> e o próximo <span> de outra atividade
    # (Terço, Adoração, Curso, etc.)
    m_bloco = re.search(
        r"<span[^>]*>\s*Missa\s*</span>\s*<br\s*/?>\s*<ul[^>]*>(.*?)</ul>",
        html, re.IGNORECASE | re.DOTALL,
    )
    if not m_bloco:
        return None
    bloco_html = m_bloco.group(1)

    # Cada <li> contém um dia + horários. Splita por "<li" preservando texto.
    items = re.split(r"<li[^>]*>", bloco_html)
    horarios_por_dia: dict[str, list[str]] = {}

    for item in items:
        if not item.strip():
            continue
        # Limpa HTML e entidades, junta em uma linha
        texto = re.sub(r"<[^>]+>", " ", item)
        texto = re.sub(r"&nbsp;", " ", texto)
        texto = re.sub(r"\s+", " ", texto).strip()
        if not texto:
            continue

        m_dia = _RE_DIA.match(texto)
        if not m_dia:
            continue
        dia_raw = m_dia.group(1).lower().replace("  ", " ")
        # Normaliza variações ("Segunda feira" → "Segunda-feira")
        dia_raw_norm = re.sub(r"\s+feira", "-feira", dia_raw)
        dia = _DIAS_MAP.get(dia_raw_norm)
        if not dia:
            # Tenta sem o sufixo "feira"
            base = dia_raw.split("-")[0].split(" ")[0]
            for k, v in _DIAS_MAP.items():
                if k.startswith(base) or base in k:
                    dia = v
                    break
        if not dia:
            continue

        horas = _normalizar_horas(texto[m_dia.end():])
        if horas:
            horarios_por_dia.setdefault(dia, []).extend(horas)

    if not horarios_por_dia:
        return None

    # Dedupe horários por dia + monta string final ordenada
    partes = []
    for dia in _DIAS_ORDEM:
        if dia in horarios_por_dia:
            horas_unicas = list(dict.fromkeys(horarios_por_dia[dia]))
            partes.append(f"{dia}: {', '.join(horas_unicas)}")
    return " | ".join(partes) if partes else None


def iterar_todos_locais() -> Iterator[dict]:
    """Generator que percorre todas as paróquias e produz cada local de culto.

    Cada item tem: nome, endereco, cidade, estado, cep, telefone, email, lat, lng, paroquia.
    Bom pra alimentar import com progresso.
    """
    ids = listar_ids_paroquias()
    logger.info("Encontrou %d IDs de paróquias", len(ids))
    for i, id_p in enumerate(ids, 1):
        detalhes = buscar_detalhes_paroquia(id_p)
        if not detalhes:
            continue
        for local in detalhes["locais"]:
            yield local
        time.sleep(0.3)  # gentle rate limit
        if i % 20 == 0:
            logger.info("Processadas %d/%d paróquias", i, len(ids))
