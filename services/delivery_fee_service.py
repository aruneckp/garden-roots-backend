"""
Delivery fee calculation using OneMap (address lookup) + Google Distance Matrix (fee).

Address resolution flow:
  1. OneMap.sg API (free, no API key, Singapore-specific) → street address + area name
     e.g. postal 542298 → street="Blk 298 Tampines Street 22", area="Tampines"
  2a. If area is in FLAT_FEE_AREAS → return near fee immediately (no Distance Matrix call)
  2b. Otherwise → Google Distance Matrix → fee based on driving distance

All thresholds, fees, and special zones are configured via environment variables.
Falls back to far fee on any error so orders are never under-charged.
"""

import logging
import re
from decimal import Decimal
from typing import Optional

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

GOOGLE_DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
GOOGLE_GEOCODING_URL        = "https://maps.googleapis.com/maps/api/geocode/json"
ONEMAP_SEARCH_URL           = "https://www.onemap.gov.sg/api/common/elastic/search"
SINGAPORE_COUNTRY_CODE      = "SG"

# Singapore town / estate name prefix lookup.
# Road names start with the estate, e.g. "TAMPINES STREET 22", "ANG MO KIO AVENUE 3".
# Sorted longest-first at build time so we always match the most specific prefix.
_TOWN_PREFIXES: dict[str, str] = {
    "ANG MO KIO":    "Ang Mo Kio",
    "BUKIT PANJANG": "Bukit Panjang",
    "BUKIT TIMAH":   "Bukit Timah",
    "BUKIT BATOK":   "Bukit Batok",
    "BUKIT MERAH":   "Bukit Merah",
    "CHOA CHU KANG": "Choa Chu Kang",
    "MARINE PARADE": "Marine Parade",
    "BUONA VISTA":   "Buona Vista",
    "PASIR RIS":     "Pasir Ris",
    "TOA PAYOH":     "Toa Payoh",
    "BOON LAY":      "Boon Lay",
    "KENT RIDGE":    "Kent Ridge",
    "TAMPINES":      "Tampines",
    "PUNGGOL":       "Punggol",
    "SENGKANG":      "Sengkang",
    "WOODLANDS":     "Woodlands",
    "SEMBAWANG":     "Sembawang",
    "SERANGOON":     "Serangoon",
    "HOUGANG":       "Hougang",
    "BEDOK":         "Bedok",
    "JURONG":        "Jurong",
    "YISHUN":        "Yishun",
    "BISHAN":        "Bishan",
    "CLEMENTI":      "Clementi",
    "GEYLANG":       "Geylang",
    "KALLANG":       "Kallang",
    "CHANGI":        "Changi",
    "NOVENA":        "Novena",
    "ORCHARD":       "Orchard",
    "QUEENSTOWN":    "Queenstown",
    "PIONEER":       "Pioneer",
    "TENGAH":        "Tengah",
    "SIMEI":         "Simei",
    "DOVER":         "Dover",
}

# Pre-sort keys by descending length so longer prefixes are checked first
_SORTED_TOWN_PREFIXES = sorted(_TOWN_PREFIXES.items(), key=lambda kv: len(kv[0]), reverse=True)

# Singapore HDB postal code 2-digit prefix → area name for known flat-fee zones.
# Used as a fallback when OneMap returns no results (e.g. auth required).
_POSTAL_PREFIX_TO_AREA: dict[str, str] = {
    "51": "Pasir Ris",
    "52": "Tampines",
    "53": "Tampines",
    "54": "Sengkang",
    "55": "Sengkang",
    "82": "Punggol",
    "83": "Punggol",
}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_flat_fee_areas() -> set:
    """Return the lowercase set of area names that always get the near fee."""
    return {a.strip().lower() for a in settings.flat_fee_areas.split(",") if a.strip()}


def _area_from_postal_code(postal_code: str) -> str:
    """Fallback: infer area from 2-digit postal prefix for known flat-fee zones."""
    if len(postal_code) >= 2:
        return _POSTAL_PREFIX_TO_AREA.get(postal_code[:2], "")
    return ""


def _extract_area_from_road(road_name: str) -> str:
    """Infer the Singapore estate/town name from a road name."""
    road_upper = road_name.upper()
    for prefix, town in _SORTED_TOWN_PREFIXES:
        if road_upper.startswith(prefix):
            return town
    return ""


def _extract_area_from_text(text: str) -> str:
    """Find a known town name anywhere in the given text (substring match)."""
    text_upper = text.upper()
    for prefix, town in _SORTED_TOWN_PREFIXES:
        if prefix in text_upper:
            return town
    return ""


def _parse_onemap_result(data: dict) -> dict:
    """
    Extract street address and area from a OneMap search response.
    Returns {"area": str, "street": str}.
    """
    result = {"area": "", "street": ""}
    results = data.get("results", [])
    if not results:
        return result

    first = results[0]
    blk_no    = (first.get("BLK_NO") or "").strip()
    road_name = (first.get("ROAD_NAME") or "").strip()
    building  = (first.get("BUILDING") or "").strip()

    # Construct a human-readable street line
    if blk_no and blk_no.upper() != "NIL":
        result["street"] = f"Blk {blk_no} {road_name.title()}"
    elif building and building.upper() != "NIL":
        result["street"] = building.title()
    else:
        result["street"] = road_name.title()

    # Infer area from the road name; fall back to full address text
    area = _extract_area_from_road(road_name)
    if not area:
        full_address = (first.get("ADDRESS") or "").strip()
        area = _extract_area_from_text(full_address)
    result["area"] = area
    return result


def _format_address(postal_code: str) -> str:
    return f"{postal_code}, {SINGAPORE_COUNTRY_CODE}"


def _build_distance_params(postal_code: str) -> dict:
    return {
        "origins":      _format_address(settings.delivery_source_postal),
        "destinations": _format_address(postal_code),
        "key":          settings.google_maps_api_key,
        "mode":         "driving",
        "units":        "metric",
    }


def _parse_distance_meters(response_data: dict) -> Optional[int]:
    """Extract driving distance in metres from a Distance Matrix response row."""
    if response_data.get("status") != "OK":
        logger.warning("Google Distance Matrix top-level error: %s", response_data.get("status"))
        return None
    rows = response_data.get("rows", [])
    elements = rows[0].get("elements", []) if rows else []
    if not elements:
        return None
    element = elements[0]
    if element.get("status") != "OK":
        logger.warning("Distance element error: %s", element.get("status"))
        return None
    return element.get("distance", {}).get("value")  # metres


def _fee_from_meters(distance_meters: Optional[int]) -> Decimal:
    """Map a driving distance (metres) to the correct delivery fee."""
    far_fee  = Decimal(str(settings.delivery_far_fee))
    near_fee = Decimal(str(settings.delivery_near_fee))
    if distance_meters is None:
        return far_fee
    return near_fee if (distance_meters / 1000.0) <= settings.delivery_near_max_km else far_fee


# ── OneMap location helpers (async + sync) ───────────────────────────────────

async def _get_location_async(postal_code: str) -> dict:
    """Async: call OneMap to resolve postal code → {area, street}."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(ONEMAP_SEARCH_URL, params={
                "searchVal":      postal_code,
                "returnGeom":     "N",
                "getAddrDetails": "Y",
                "pageNum":        1,
            })
            resp.raise_for_status()
            return _parse_onemap_result(resp.json())
    except Exception as exc:
        logger.warning("OneMap async lookup failed for %s: %s", postal_code, exc)
        return {"area": "", "street": ""}


def _get_location_sync(postal_code: str) -> dict:
    """Sync: call OneMap to resolve postal code → {area, street}."""
    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(ONEMAP_SEARCH_URL, params={
                "searchVal":      postal_code,
                "returnGeom":     "N",
                "getAddrDetails": "Y",
                "pageNum":        1,
            })
            resp.raise_for_status()
            return _parse_onemap_result(resp.json())
    except Exception as exc:
        logger.warning("OneMap sync lookup failed for %s: %s", postal_code, exc)
        return {"area": "", "street": ""}


# ── Google Geocoding area helpers (fallback when OneMap is unavailable) ───────

_GEOCODING_AREA_TYPES = ("neighborhood", "sublocality_level_1", "sublocality")


def _area_from_geocoding_result(data: dict) -> str:
    """Extract area name from a Google Geocoding API response dict."""
    if data.get("status") != "OK" or not data.get("results"):
        return ""
    result = data["results"][0]
    # 1. Try specific address component types
    for comp in result.get("address_components", []):
        if any(t in comp.get("types", []) for t in _GEOCODING_AREA_TYPES):
            return comp["long_name"]
    # 2. Fall back to scanning the formatted_address with known town prefixes
    formatted = result.get("formatted_address", "")
    if formatted:
        return _extract_area_from_text(formatted)
    return ""


async def _get_area_from_geocoding_async(postal_code: str) -> str:
    """Resolve area name via Google Geocoding API (async)."""
    if not settings.google_maps_api_key:
        return ""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(GOOGLE_GEOCODING_URL, params={
                "address":    f"Singapore {postal_code}",
                "key":        settings.google_maps_api_key,
                "components": "country:SG",
            })
            resp.raise_for_status()
            return _area_from_geocoding_result(resp.json())
    except Exception as exc:
        logger.warning("Geocoding async failed for %s: %s", postal_code, exc)
    return ""


def _get_area_from_geocoding_sync(postal_code: str) -> str:
    """Resolve area name via Google Geocoding API (sync)."""
    if not settings.google_maps_api_key:
        return ""
    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(GOOGLE_GEOCODING_URL, params={
                "address":    f"Singapore {postal_code}",
                "key":        settings.google_maps_api_key,
                "components": "country:SG",
            })
            resp.raise_for_status()
            return _area_from_geocoding_result(resp.json())
    except Exception as exc:
        logger.warning("Geocoding sync failed for %s: %s", postal_code, exc)
    return ""


# ── Public async interface (used by the API endpoint) ────────────────────────

async def get_delivery_fee_async(postal_code: str) -> dict:
    """
    Return fee, street address, area name, and zone for the given postal code.
    Uses OneMap for address resolution and Google Distance Matrix for fee calculation.
    Falls back gracefully on any failure.
    """
    far_fee        = float(settings.delivery_far_fee)
    near_fee       = float(settings.delivery_near_fee)
    free_threshold = float(settings.delivery_free_threshold)
    fallback = {"fee": far_fee, "area": "", "street": "", "zone": "Standard Area", "free_threshold": free_threshold}

    # Step 1: Resolve address via OneMap (no API key required)
    location = await _get_location_async(postal_code)
    area   = location["area"]
    street = location["street"]

    # If OneMap didn't return an area (e.g. auth required), fall back to postal prefix
    if not area:
        area = _area_from_postal_code(postal_code)

    # Step 2a: Flat fee for special zones — skip Distance Matrix entirely
    if area and area.lower() in _get_flat_fee_areas():
        return {"fee": near_fee, "area": area, "street": street, "zone": "Near Area", "free_threshold": free_threshold}

    # Step 2b: Distance-based fee for all other areas
    if not settings.google_maps_api_key:
        logger.warning("GOOGLE_MAPS_API_KEY not set — returning default far fee")
        return {**fallback, "area": area, "street": street, "free_threshold": free_threshold, "note": "Distance API not configured"}

    # Resolve area name via Geocoding if still unknown
    if not area:
        area = await _get_area_from_geocoding_async(postal_code)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                GOOGLE_DISTANCE_MATRIX_URL, params=_build_distance_params(postal_code)
            )
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        logger.error("Google Distance Matrix async call failed: %s", exc)
        return {**fallback, "area": area, "street": street}

    distance_meters = _parse_distance_meters(data)
    fee    = _fee_from_meters(distance_meters)
    is_near = float(fee) == near_fee
    return {
        "fee":            float(fee),
        "area":           area,
        "street":         street,
        "zone":           "Near Area" if is_near else "Standard Area",
        "free_threshold": free_threshold,
    }


# ── Public sync interface (used by order_service inside a DB transaction) ────

def get_delivery_fee_sync(postal_code: Optional[str]) -> Decimal:
    """
    Synchronous delivery fee lookup for use inside SQLAlchemy transactions.
    Applies the same flat-fee-zone logic as the async version.
    Returns the far fee on any failure so orders are never under-charged.
    """
    far_fee  = Decimal(str(settings.delivery_far_fee))
    near_fee = Decimal(str(settings.delivery_near_fee))

    if not postal_code or len(postal_code) != 6:
        return far_fee

    # Check flat fee zones first via OneMap, fall back to postal prefix
    location = _get_location_sync(postal_code)
    area = location["area"]
    if not area:
        area = _area_from_postal_code(postal_code)
    if area and area.lower() in _get_flat_fee_areas():
        return near_fee

    # Distance-based for other areas
    if not settings.google_maps_api_key:
        logger.warning("GOOGLE_MAPS_API_KEY not set — defaulting to far fee in order_service")
        return far_fee

    # area name not needed for fee calculation in sync path — skip geocoding call

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                GOOGLE_DISTANCE_MATRIX_URL, params=_build_distance_params(postal_code)
            )
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        logger.error("Google Distance Matrix sync call failed: %s", exc)
        return far_fee

    return _fee_from_meters(_parse_distance_meters(data))
