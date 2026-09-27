"""Agoda Partners (CID) search links — replaces A8 Agoda click URLs.

CID 1969838 = Approval Site. Deep-link with city= when possible.

City IDs below are partner-confirmed (2026-09). If a hub is missing, ask
for the Agoda city code rather than guessing.
"""

from __future__ import annotations

import math
import os
from typing import Any
from urllib.parse import urlencode

AGODA_CID = os.getenv("AGODA_PARTNERS_CID", "1969838").strip() or "1969838"

# Partner-confirmed Agoda city IDs (hub coords for nearest-city matching).
AGODA_CITIES: tuple[dict[str, Any], ...] = (
    # Japan
    {"id": 5085, "name": "Tokyo", "lat": 35.6812, "lng": 139.7671, "country": "jp"},
    {"id": 9590, "name": "Osaka", "lat": 34.6937, "lng": 135.5023, "country": "jp"},
    {"id": 1784, "name": "Kyoto", "lat": 35.0116, "lng": 135.7681, "country": "jp"},
    {"id": 16527, "name": "Fukuoka", "lat": 33.5904, "lng": 130.4017, "country": "jp"},
    {"id": 3435, "name": "Sapporo", "lat": 43.0618, "lng": 141.3545, "country": "jp"},
    {"id": 13740, "name": "Nagoya", "lat": 35.1815, "lng": 136.9066, "country": "jp"},
    {"id": 717899, "name": "Okinawa", "lat": 26.3344, "lng": 127.8056, "country": "jp"},
    {"id": 5235, "name": "Kobe", "lat": 34.6901, "lng": 135.1956, "country": "jp"},
    {"id": 10345, "name": "Sendai", "lat": 38.2682, "lng": 140.8694, "country": "jp"},
    {"id": 10554, "name": "Hiroshima", "lat": 34.3853, "lng": 132.4553, "country": "jp"},
    # Korea
    {"id": 14690, "name": "Seoul", "lat": 37.5665, "lng": 126.9780, "country": "kr"},
    {"id": 17172, "name": "Busan", "lat": 35.1796, "lng": 129.0756, "country": "kr"},
    {"id": 16901, "name": "Jeju", "lat": 33.4996, "lng": 126.5312, "country": "kr"},
    # Thailand
    {"id": 9395, "name": "Bangkok", "lat": 13.7563, "lng": 100.5018, "country": "th"},
    {"id": 8584, "name": "Pattaya", "lat": 12.9236, "lng": 100.8825, "country": "th"},
    {"id": 16056, "name": "Phuket", "lat": 7.8804, "lng": 98.3923, "country": "th"},
    # Vietnam
    {"id": 13170, "name": "Ho Chi Minh City", "lat": 10.8231, "lng": 106.6297, "country": "vn"},
    {"id": 16440, "name": "Da Nang", "lat": 16.0544, "lng": 108.2022, "country": "vn"},
    # US / Pacific (okcaddie overseas)
    {"id": 6126, "name": "Guam", "lat": 13.4443, "lng": 144.7937, "country": "gu"},
    {"id": 10921, "name": "Honolulu", "lat": 21.3069, "lng": -157.8583, "country": "us"},
)

_COUNTRY_DEFAULT = {
    "jp": 5085,  # Tokyo
    "kr": 14690,  # Seoul (NOT Jeju 16901)
    "th": 9395,  # Bangkok
    "vn": 13170,  # HCMC
    "gu": 6126,
    "us": 10921,
}

_HL = {
    "en": "en-us",
    "ko": "ko-kr",
    "kr": "ko-kr",
    "ja": "ja-jp",
}


def hl_for_lang(lang: str | None) -> str:
    code = (lang or "en").strip().lower()
    return _HL.get(code, "en-us")


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest_city_id(
    lat: float | None,
    lng: float | None,
    *,
    country: str | None = None,
    max_km: float = 450.0,
) -> int | None:
    """Pick the closest Agoda city hub, optionally filtered by country code."""
    try:
        lat_f = float(lat) if lat is not None else None
        lng_f = float(lng) if lng is not None else None
    except (TypeError, ValueError):
        lat_f = lng_f = None

    cc = (country or "").strip().lower()
    if cc in ("japan",):
        cc = "jp"
    if cc in ("korea", "south korea", "republic of korea"):
        cc = "kr"
    if cc in ("thailand",):
        cc = "th"
    if cc in ("vietnam", "viet nam"):
        cc = "vn"
    if cc in ("guam",):
        cc = "gu"
    if cc in ("usa", "united states", "hawaii"):
        cc = "us"

    pool = [c for c in AGODA_CITIES if not cc or c["country"] == cc]
    if not pool:
        pool = list(AGODA_CITIES)

    if lat_f is None or lng_f is None:
        if cc and cc in _COUNTRY_DEFAULT:
            return _COUNTRY_DEFAULT[cc]
        return None

    best = None
    best_d = float("inf")
    for c in pool:
        d = _haversine_km(lat_f, lng_f, float(c["lat"]), float(c["lng"]))
        if d < best_d:
            best_d = d
            best = c
    if best is None:
        return _COUNTRY_DEFAULT.get(cc)
    if best_d > max_km:
        return _COUNTRY_DEFAULT.get(cc) or int(best["id"])
    return int(best["id"])


def partner_search_url(
    *,
    lang: str | None = "en",
    city_id: int | str | None = None,
    cid: str | None = None,
) -> str:
    """Build https://www.agoda.com/partners/partnersearch.aspx?...

    Always include city= — empty destination search fails on Agoda (worldwide error UI).
    Default Tokyo (5085) when caller omits city.
    """
    city = str(city_id).strip() if city_id is not None and str(city_id).strip() else "5085"
    params: dict[str, str] = {
        "pcs": "1",
        "cid": (cid or AGODA_CID).strip(),
        "hl": hl_for_lang(lang),
        "city": city,
    }
    return "https://www.agoda.com/partners/partnersearch.aspx?" + urlencode(params)


def url_for_location(
    *,
    lang: str | None = "en",
    lat: float | None = None,
    lng: float | None = None,
    country: str | None = None,
    default_city: int | None = None,
) -> str:
    city = nearest_city_id(lat, lng, country=country)
    if city is None:
        city = default_city
    return partner_search_url(lang=lang, city_id=city)
