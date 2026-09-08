"""Geocoding e descoberta de igrejas via Nominatim (OpenStreetMap).

Política de uso da API pública do Nominatim:
- User-Agent identificável (obrigatório)
- Rate limit: 1 request/segundo
- Atribuição: dados © OpenStreetMap contributors

Estratégia: quando a busca local não retorna nada, consulta Nominatim, filtra
por igrejas católicas e persiste no BD para próximas buscas (catálogo incremental).
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "DiaDeMissa-App/1.0 (admin@diademissa.app)"

# Rate limiter simples — Nominatim exige máximo 1 req/s
_last_request_ts = 0.0


def _respeitar_rate_limit():
    global _last_request_ts
    agora = time.time()
    delta = agora - _last_request_ts
    if delta < 1.05:  # margem
        time.sleep(1.05 - delta)
    _last_request_ts = time.time()


def buscar_igrejas_osm(
    termo: str,
    bias_pais: str = "br",
    bias_cidade: str = "Rio de Janeiro",
    limite: int = 10,
) -> list[dict]:
    """Procura igrejas/templos via Nominatim.

    Estratégia:
    1. Query "igreja católica {termo}" para focar em locais de culto católico
    2. Fallback: query mais ampla "{termo} igreja" se nada vier
    3. Inclui `bias_cidade` na query pra evitar match em outros municípios homônimos

    Retorna lista de dicts no formato compatível com o model Igreja:
        [{"nome", "endereco", "cidade", "estado", "lat", "lng"}]
    """
    if not termo or len(termo.strip()) < 3:
        return []

    # Inclui bias_cidade na query pra desambiguar (ex.: "leblon Rio de Janeiro" em vez de só "leblon")
    suffix = f" {bias_cidade}" if bias_cidade else ""
    candidatos = [
        f"igreja católica {termo}{suffix}",
        f"paróquia {termo}{suffix}",
        f"capela {termo}{suffix}",
        f"santuário {termo}{suffix}",
    ]

    encontradas: list[dict] = []
    nomes_vistos: set[str] = set()

    for query in candidatos:
        try:
            _respeitar_rate_limit()
            resp = httpx.get(
                NOMINATIM_URL,
                params={
                    "q": query,
                    "format": "json",
                    "addressdetails": 1,
                    "countrycodes": bias_pais,
                    "limit": limite,
                    "accept-language": "pt-BR",
                },
                headers={"User-Agent": USER_AGENT},
                timeout=8.0,
            )
            if resp.status_code != 200:
                logger.warning("Nominatim status %s", resp.status_code)
                continue
            for item in resp.json():
                nome = (item.get("name") or item.get("display_name", "").split(",")[0]).strip()
                if not nome or nome.lower() in nomes_vistos:
                    continue
                # Filtra: queremos igrejas/templos cristãos
                tipo = (item.get("type") or "").lower()
                klass = (item.get("class") or "").lower()
                # Aceita amenity=place_of_worship, building=church, ou nome contendo igreja/paróquia/capela
                aceita = (
                    tipo == "place_of_worship"
                    or "church" in tipo
                    or "chapel" in tipo
                    or "cathedral" in tipo
                    or any(p in nome.lower() for p in ("igreja", "paróquia", "paroquia", "capela", "catedral", "santuário", "santuario"))
                )
                if not aceita:
                    continue

                addr = item.get("address", {}) or {}
                endereco = ", ".join(filter(None, [
                    addr.get("road") or addr.get("pedestrian"),
                    addr.get("house_number"),
                    addr.get("suburb") or addr.get("neighbourhood"),
                ])) or None
                cidade = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality")
                estado = addr.get("state_code") or _abreviar_estado(addr.get("state"))

                # Filtra: cidade tem que bater com bias_cidade (case insensitive) se foi fornecido
                if bias_cidade and cidade and bias_cidade.lower() not in (cidade or "").lower() and (cidade or "").lower() not in bias_cidade.lower():
                    continue

                try:
                    lat = float(item["lat"])
                    lng = float(item["lon"])
                except (KeyError, ValueError):
                    continue

                encontradas.append({
                    "nome": nome,
                    "endereco": endereco,
                    "cidade": cidade,
                    "estado": estado,
                    "cep": addr.get("postcode"),
                    "telefone": None,
                    "site": None,
                    "lat": lat,
                    "lng": lng,
                    "observacoes": "Importada de OpenStreetMap",
                })
                nomes_vistos.add(nome.lower())
                if len(encontradas) >= limite:
                    return encontradas
        except Exception:
            logger.exception("Falha consultando Nominatim para %r", query)

    return encontradas


OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def buscar_igrejas_overpass(lat: float, lng: float, raio_m: int = 2000) -> list[dict]:
    """Lista TODAS as igrejas (amenity=place_of_worship) num raio em torno de uma coordenada.

    Overpass API é o jeito profissional de listar POIs por área do OpenStreetMap.
    Filtra preferencialmente católicas, mas inclui cristãs em geral.
    """
    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="place_of_worship"](around:{raio_m},{lat},{lng});
      way["amenity"="place_of_worship"](around:{raio_m},{lat},{lng});
    );
    out center tags;
    """
    try:
        _respeitar_rate_limit()
        resp = httpx.post(
            OVERPASS_URL,
            data={"data": query},
            headers={"User-Agent": USER_AGENT},
            timeout=30.0,
        )
        if resp.status_code != 200:
            logger.warning("Overpass status %s", resp.status_code)
            return []
        elements = resp.json().get("elements", [])
    except Exception:
        logger.exception("Falha consultando Overpass")
        return []

    # Padrões de nome tipicamente católicos (usados quando OSM não traz denomination)
    PADROES_CATOLICOS = (
        "paróquia", "paroquia", "capela", "catedral", "santuário", "santuario",
        "igreja católica", "igreja catolica", "matriz",
        "nossa senhora", "n. sra", "n.sra", "n sra",
        "são ", "sao ", "santo ", "santa ", "são,", "santo,", "santa,",
        "sagrado", "imaculada", "redentor", "cristo",
    )
    PADROES_NAO_CATOLICOS = (
        "presbiteriana", "prebisteriana", "metodista", "luterana",
        "messiânica", "messianica", "assembleia de deus", "batista",
        "adventista", "pentecostal", "universal", "evangélica", "evangelica",
        "ministério", "ministerio", "renovada", "anglicana", "ortodoxa",
        "palavras de vida", "kingdom hall", "testemunhas",
    )

    igrejas: list[dict] = []
    nomes_vistos: set[str] = set()
    for el in elements:
        tags = el.get("tags", {}) or {}
        relig = (tags.get("religion") or "").lower()
        denom = (tags.get("denomination") or "").lower()
        nome = tags.get("name") or tags.get("addr:name")
        if not nome:
            continue
        nome_lower = nome.lower()

        # Rejeita explicitamente não-cristãs ou não-católicas conhecidas
        if relig and relig != "christian":
            continue
        if any(p in nome_lower for p in PADROES_NAO_CATOLICOS):
            continue
        if denom and denom not in ("catholic", "roman_catholic", ""):
            continue

        # Aceita se: denomination explicitamente católica OU nome tem padrão católico
        eh_catolica = (
            denom in ("catholic", "roman_catholic")
            or any(p in nome_lower for p in PADROES_CATOLICOS)
        )
        if not eh_catolica:
            continue
        # Dedupe por nome (OSM frequentemente tem node + way pra mesma POI)
        nome_norm = nome.strip().lower()
        if nome_norm in nomes_vistos:
            continue
        nomes_vistos.add(nome_norm)
        # Coordenadas: node direto, way usa center
        if el.get("type") == "node":
            la, lo = el.get("lat"), el.get("lon")
        else:
            center = el.get("center", {})
            la, lo = center.get("lat"), center.get("lon")
        if la is None or lo is None:
            continue

        endereco_partes = []
        if tags.get("addr:street"):
            endereco_partes.append(tags["addr:street"])
            if tags.get("addr:housenumber"):
                endereco_partes.append(tags["addr:housenumber"])
        if tags.get("addr:suburb"):
            endereco_partes.append(tags["addr:suburb"])
        endereco = ", ".join(endereco_partes) or None

        igrejas.append({
            "nome": nome,
            "endereco": endereco,
            "cidade": tags.get("addr:city"),
            "estado": _abreviar_estado(tags.get("addr:state")),
            "cep": tags.get("addr:postcode"),
            "telefone": tags.get("phone") or tags.get("contact:phone"),
            "site": tags.get("website") or tags.get("contact:website"),
            "lat": float(la),
            "lng": float(lo),
            "observacoes": "Importada de OpenStreetMap (Overpass)",
        })
    return igrejas


NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"


def reverse_geocode(lat: float, lng: float) -> Optional[dict]:
    """Reverse geocoding via Nominatim — descobre endereço a partir de lat/lng.

    Retorna dict com {endereco, cidade, estado, cep} ou None se falhar.
    Usado para enriquecer igrejas importadas do Overpass que vieram sem addr:street.
    """
    try:
        _respeitar_rate_limit()
        resp = httpx.get(
            NOMINATIM_REVERSE_URL,
            params={
                "lat": lat,
                "lon": lng,
                "format": "json",
                "addressdetails": 1,
                "accept-language": "pt-BR",
                "zoom": 18,  # nível de prédio/rua
            },
            headers={"User-Agent": USER_AGENT},
            timeout=8.0,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        addr = data.get("address", {}) or {}
        rua = addr.get("road") or addr.get("pedestrian") or addr.get("residential")
        numero = addr.get("house_number")
        bairro = addr.get("suburb") or addr.get("neighbourhood") or addr.get("quarter")
        partes = []
        if rua:
            partes.append(rua)
            if numero:
                partes.append(numero)
        if bairro:
            partes.append(bairro)
        endereco = ", ".join(partes) or None
        cidade = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality")
        return {
            "endereco": endereco,
            "cidade": cidade,
            "estado": _abreviar_estado(addr.get("state")) or addr.get("state_code"),
            "cep": addr.get("postcode"),
        }
    except Exception:
        logger.exception("Falha em reverse geocode (%s, %s)", lat, lng)
        return None


def geocodificar_bairro(
    nome_bairro: str,
    cidade: Optional[str] = None,
    bias_lat: Optional[float] = None,
    bias_lng: Optional[float] = None,
) -> Optional[tuple[float, float]]:
    """Retorna lat/lng do centro de um bairro/região.

    Estratégia de bias (do mais forte pro mais fraco):
    - Se `bias_lat`+`bias_lng` informados → usa viewbox de ~50km em volta pra priorizar local.
    - Se `cidade` informada → append no query ("bairro, cidade, Brasil").
    - Caso contrário → query global no Brasil ("bairro, Brasil"). Útil pra termos
      como "moema" achar Moema-SP em vez de Moema-Paquetá-RJ.
    """
    try:
        _respeitar_rate_limit()
        if cidade:
            q = f"{nome_bairro}, {cidade}, Brasil"
        else:
            q = f"{nome_bairro}, Brasil"
        params = {
            "q": q,
            "format": "json",
            "limit": 1,
            "accept-language": "pt-BR",
            "countrycodes": "br",
        }
        if bias_lat is not None and bias_lng is not None:
            # viewbox ~50km em torno do ponto (~0.45 graus de lat/lng)
            delta = 0.45
            params["viewbox"] = f"{bias_lng - delta},{bias_lat + delta},{bias_lng + delta},{bias_lat - delta}"
            params["bounded"] = 0  # apenas viés, não restritivo
        resp = httpx.get(
            NOMINATIM_URL,
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=8.0,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data:
            return None
        return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        logger.exception("Falha geocodificando %r", nome_bairro)
        return None


_ESTADOS = {
    "Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM", "Bahia": "BA",
    "Ceará": "CE", "Distrito Federal": "DF", "Espírito Santo": "ES", "Goiás": "GO",
    "Maranhão": "MA", "Mato Grosso": "MT", "Mato Grosso do Sul": "MS", "Minas Gerais": "MG",
    "Pará": "PA", "Paraíba": "PB", "Paraná": "PR", "Pernambuco": "PE", "Piauí": "PI",
    "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN", "Rio Grande do Sul": "RS",
    "Rondônia": "RO", "Roraima": "RR", "Santa Catarina": "SC", "São Paulo": "SP",
    "Sergipe": "SE", "Tocantins": "TO",
}


def _abreviar_estado(nome: Optional[str]) -> Optional[str]:
    if not nome:
        return None
    return _ESTADOS.get(nome.strip(), nome[:2].upper() if len(nome) == 2 else None)
