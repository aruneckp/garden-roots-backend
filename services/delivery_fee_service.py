"""
Delivery fee calculation using OneMap for address lookup.

Resolution flow:
  1. OneMap.sg API → street + area name  (requires ONEMAP_API_TOKEN)
  2. Postal-prefix fallback if OneMap unavailable
  3. Zone match: Near ($5) → Mid ($6, street override) → High ($8) → far fee ($8) for unknown areas

All fees and zone lists are configured via environment variables.
"""

import logging
from decimal import Decimal
from typing import Optional

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

ONEMAP_SEARCH_URL = "https://www.onemap.gov.sg/api/common/elastic/search"
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
    "SIGLAP":        "Siglap",
    "TUAS":          "Tuas",
}

# Pre-sort keys by descending length so longer prefixes are checked first
_SORTED_TOWN_PREFIXES = sorted(_TOWN_PREFIXES.items(), key=lambda kv: len(kv[0]), reverse=True)

# Singapore HDB postal code 2-digit prefix → area name for known flat-fee zones.
# Used as a fallback when OneMap returns no results (e.g. auth required).
_POSTAL_PREFIX_TO_AREA: dict[str, str] = {
    "45": "Siglap",
    "46": "Bedok",
    "51": "Pasir Ris",
    "52": "Tampines",
    "53": "Sengkang",   # 53xxxx = Sengkang (was wrongly mapped to Tampines)
    "54": "Sengkang",
    "55": "Sengkang",
    "73": "Woodlands",
    "75": "Sembawang",
    "76": "Yishun",
    "82": "Punggol",
    "83": "Punggol",
}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_flat_fee_areas() -> set:
    """Return the lowercase set of area names that always get the near fee ($5)."""
    return {a.strip().lower() for a in settings.flat_fee_areas.split(",") if a.strip()}


def _get_mid_fee_areas() -> set:
    """Return the lowercase set of area names that get the mid fee ($6)."""
    return {a.strip().lower() for a in settings.mid_fee_areas.split(",") if a.strip()}


def _is_mid_fee_street(street: str) -> bool:
    """Return True if the street name contains a mid-fee keyword (e.g. compassvale, rivervale)."""
    if not street or not settings.mid_fee_streets:
        return False
    street_lower = street.lower()
    return any(kw.strip().lower() in street_lower for kw in settings.mid_fee_streets.split(",") if kw.strip())


def _get_high_fee_areas() -> set:
    """Return the lowercase set of area names that get the high fee ($8, Zone 3)."""
    return {a.strip().lower() for a in settings.high_fee_areas.split(",") if a.strip()}


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


# ── OneMap location helpers (async + sync) ───────────────────────────────────

def _onemap_headers() -> dict:
    """Return Authorization header if ONEMAP_API_TOKEN is configured."""
    token = getattr(settings, "onemap_api_token", "")
    return {"Authorization": token} if token else {}


async def _get_location_async(postal_code: str) -> dict:
    """Async: call OneMap to resolve postal code → {area, street}."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(ONEMAP_SEARCH_URL, headers=_onemap_headers(), params={
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
            resp = client.get(ONEMAP_SEARCH_URL, headers=_onemap_headers(), params={
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


# ── Public async interface (used by the API endpoint) ────────────────────────

async def get_delivery_fee_async(postal_code: str) -> dict:
    """
    Return fee, street, area, and zone for the given postal code.
    Near ($5) → Mid street override ($6) → Mid area ($6) → High ($8) → far fee ($8) for unknown areas.
    """
    far_fee        = float(settings.delivery_far_fee)
    near_fee       = float(settings.delivery_near_fee)
    mid_fee        = float(settings.delivery_mid_fee)
    high_fee       = float(settings.delivery_high_fee)
    free_threshold = float(settings.delivery_free_threshold)
    fallback = {"fee": far_fee, "area": "", "street": "", "zone": "Standard Area", "free_threshold": free_threshold}

    # Step 1: Resolve address via OneMap
    location = await _get_location_async(postal_code)
    area   = location["area"]
    street = location["street"]

    # If OneMap didn't return an area, fall back to postal prefix
    if not area:
        area = _area_from_postal_code(postal_code)

    # Step 2a: Street-keyword mid zone — e.g. Compassvale/Rivervale within Sengkang
    if _is_mid_fee_street(street):
        return {"fee": mid_fee, "area": area, "street": street, "zone": "Mid Area", "free_threshold": free_threshold}

    # Step 2b: Zone 1 — $5 delivery
    if area and area.lower() in _get_flat_fee_areas():
        return {"fee": near_fee, "area": area, "street": street, "zone": "Near Area", "free_threshold": free_threshold}

    # Step 2c: Zone 2 — $6 delivery
    if area and area.lower() in _get_mid_fee_areas():
        return {"fee": mid_fee, "area": area, "street": street, "zone": "Mid Area", "free_threshold": free_threshold}

    # Step 2d: Zone 3 — $8 delivery
    if area and area.lower() in _get_high_fee_areas():
        return {"fee": high_fee, "area": area, "street": street, "zone": "Standard Area", "free_threshold": free_threshold}

    # Step 2e: Area not in any configured zone — charge the standard far fee
    return {**fallback, "area": area, "street": street, "free_threshold": free_threshold}


# ── Public sync interface (used by order_service inside a DB transaction) ────

def get_delivery_fee_sync(postal_code: Optional[str]) -> Decimal:
    """
    Synchronous delivery fee lookup for use inside SQLAlchemy transactions.
    Applies the same flat-fee-zone logic as the async version.
    Returns the far fee on any failure so orders are never under-charged.
    """
    far_fee  = Decimal(str(settings.delivery_far_fee))
    near_fee = Decimal(str(settings.delivery_near_fee))
    mid_fee  = Decimal(str(settings.delivery_mid_fee))
    high_fee = Decimal(str(settings.delivery_high_fee))

    if not postal_code or len(postal_code) != 6:
        return far_fee

    # Check fee zones via OneMap, fall back to postal prefix
    location = _get_location_sync(postal_code)
    area   = location["area"]
    street = location["street"]
    if not area:
        area = _area_from_postal_code(postal_code)
    if _is_mid_fee_street(street):
        return mid_fee
    if area and area.lower() in _get_flat_fee_areas():
        return near_fee
    if area and area.lower() in _get_mid_fee_areas():
        return mid_fee
    if area and area.lower() in _get_high_fee_areas():
        return high_fee

    # Area not in any configured zone — charge the standard far fee
    return far_fee
