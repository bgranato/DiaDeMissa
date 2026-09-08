"""Fallback de busca de igrejas via Google Places API (Nearby Search).

Ativo apenas se a env var GOOGLE_PLACES_API_KEY estiver definida. Caso contrário,
retorna lista vazia silenciosamente — o app continua funcionando 100% com o catálogo
oficial da Arquidiocese, e cidades fora dessa cobertura simplesmente não trazem extras.

Quando ativar:
1. Habilite a Places API (New) no Google Cloud Console.
2. Crie a key e exporte: export GOOGLE_PLACES_API_KEY="..."
3. Reinicie o backend.

Custo: $200/mês de crédito grátis (≈5k Nearby Search). Acima disso, US$32/1000.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Places API (New) — endpoint Nearby Search
PLACES_URL = "https://places.googleapis.com/v1/places:searchNearby"

# Filtros: queremos igrejas católicas. A Places API só tem o tipo genérico "church".
# Filtragem fina (denominação) é feita pelo nome no pós-processamento.
PADROES_NAO_CATOLICOS = (
    "presbiteriana", "metodista", "luterana", "messianica",
    "assembleia de deus", "batista", "adventista", "pentecostal",
    "universal", "evangélica", "evangelica", "ministério", "ministerio",
    "renovada", "anglicana", "ortodoxa", "kingdom hall", "testemunhas",
)


def _api_key() -> Optional[str]:
    """Aceita GOOGLE_PLACES_API_KEY ou GOOGLE_MAPS_API_KEY (alias)."""
    key = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip() or os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    return key or None


def geocoding_configurado() -> bool:
    """Indica se existe uma chave que permitiria chamar o Geocoding."""
    return _api_key() is not None


# Geocoding API: converte query texto → lat/lng. Free tier $200/mês ≈ 40k requests.
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


class GeocodingIndisponivelError(RuntimeError):
    """O provedor não pôde processar uma consulta válida no momento."""


def geocodificar_query_google(
    query: str,
    bias_lat: Optional[float] = None,
    bias_lng: Optional[float] = None,
) -> Optional[tuple[float, float]]:
    """Converte uma query semântica em lat/lng via Google Geocoding API.

    Funciona muito melhor que Nominatim pra queries livres tipo:
        "Igreja da PUC", "Maracanã", "Vila Mariana SP", "centro do Rio"

    Retorna ``None`` somente quando o endereço não é encontrado. Problemas de
    configuração, rede ou resposta do provedor levantam ``GeocodingIndisponivelError``
    para não culpar o endereço informado pela pessoa.
    """
    key = _api_key()
    if not key:
        raise GeocodingIndisponivelError("chave de Geocoding não configurada")

    params = {
        "address": query,
        "key": key,
        "language": "pt-BR",
        "region": "br",  # bias por país
    }
    # Bias por localização do usuário (raio em metros — ~50km)
    if bias_lat is not None and bias_lng is not None:
        params["bounds"] = f"{bias_lat - 0.45},{bias_lng - 0.45}|{bias_lat + 0.45},{bias_lng + 0.45}"

    try:
        r = httpx.get(GEOCODE_URL, params=params, timeout=10.0)
        if r.status_code != 200:
            logger.warning("Google Geocoding status %s: %s", r.status_code, r.text[:200])
            raise GeocodingIndisponivelError(f"Google Geocoding respondeu HTTP {r.status_code}")
        data = r.json()
        status = data.get("status")
        if status != "OK":
            if status == "ZERO_RESULTS":
                return None
            logger.warning("Google Geocoding status=%s message=%s", status, data.get("error_message"))
            raise GeocodingIndisponivelError(f"Google Geocoding respondeu {status or 'status desconhecido'}")
        results = data.get("results", [])
        if not results:
            return None
        loc = results[0].get("geometry", {}).get("location", {})
        lat = loc.get("lat")
        lng = loc.get("lng")
        if lat is None or lng is None:
            raise GeocodingIndisponivelError("Google Geocoding não retornou coordenadas")
        return float(lat), float(lng)
    except GeocodingIndisponivelError:
        raise
    except Exception as erro:
        logger.exception("Falha em Google Geocoding")
        raise GeocodingIndisponivelError("falha de comunicação com Google Geocoding") from erro


def buscar_igrejas_google_places(lat: float, lng: float, raio_m: int = 5000) -> list[dict]:
    """Retorna igrejas católicas próximas via Google Places API.

    Sem API key configurada, retorna [] (no-op silencioso).
    """
    key = _api_key()
    if not key:
        return []

    body = {
        "includedTypes": ["church"],
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": min(raio_m, 50000),
            }
        },
        "languageCode": "pt-BR",
        "regionCode": "BR",
    }
    headers = {
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": (
            "places.displayName,places.formattedAddress,places.location,"
            "places.nationalPhoneNumber,places.websiteUri,places.postalCode"
        ),
        "Content-Type": "application/json",
    }
    try:
        r = httpx.post(PLACES_URL, json=body, headers=headers, timeout=15.0)
        if r.status_code != 200:
            logger.warning("Google Places status %s: %s", r.status_code, r.text[:200])
            return []
        data = r.json()
    except Exception:
        logger.exception("Falha em Google Places Nearby Search")
        return []

    igrejas: list[dict] = []
    for p in data.get("places", []):
        nome = (p.get("displayName") or {}).get("text", "").strip()
        if not nome:
            continue
        nome_lower = nome.lower()
        if any(pad in nome_lower for pad in PADROES_NAO_CATOLICOS):
            continue
        loc = p.get("location", {}) or {}
        plat = loc.get("latitude")
        plng = loc.get("longitude")
        if plat is None or plng is None:
            continue
        igrejas.append({
            "nome": nome,
            "endereco": p.get("formattedAddress"),
            "cidade": None,  # Google retorna no formattedAddress; parsing fica simples
            "estado": None,
            "cep": p.get("postalCode"),
            "telefone": p.get("nationalPhoneNumber"),
            "site": p.get("websiteUri"),
            "lat": float(plat),
            "lng": float(plng),
            "observacoes": "Importada de Google Places",
        })
    return igrejas
