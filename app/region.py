"""Address / coordinates → region keys for KR Care filters (no paid APIs)."""
from __future__ import annotations

import re
from typing import Any

_LANG_SUFFIX = re.compile(r"_(en|ja|zh_tw|zh|ko)$", re.I)

SIDO_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("seoul", re.compile(r"Seoul|서울|ソウル|首尔|首爾", re.I)),
    ("busan", re.compile(r"Busan|부산|釜山|プサン", re.I)),
    ("incheon", re.compile(r"Incheon|인천|仁川", re.I)),
    ("gyeonggi", re.compile(r"Gyeonggi|경기|京畿", re.I)),
    ("daegu", re.compile(r"Daegu|대구|大邱", re.I)),
    ("daejeon", re.compile(r"Daejeon|대전|大田", re.I)),
    ("gwangju", re.compile(r"Gwangju|광주|光州", re.I)),
    ("ulsan", re.compile(r"Ulsan|울산|蔚山", re.I)),
    ("gangwon", re.compile(r"Gangwon|강원|江原", re.I)),
    ("jeju", re.compile(r"Jeju|제주|济州|濟州", re.I)),
    ("jeonbuk", re.compile(r"Jeonbuk|Jeollabuk|전북|전라북|全北", re.I)),
    ("jeonnam", re.compile(r"Jeonnam|전남|전라남|全南", re.I)),
    ("gyeongbuk", re.compile(r"Gyeongbuk|경북|경상북|庆北|慶北", re.I)),
    ("gyeongnam", re.compile(r"Gyeongnam|경남|경상남|庆南|慶南", re.I)),
    ("chungbuk", re.compile(r"Chungbuk|충북|충청북|忠北|Cheongju", re.I)),
    ("chungnam", re.compile(r"Chungnam|충남|충청남|忠南", re.I)),
]

TOP_SIDO = {"seoul", "busan", "incheon", "gyeonggi", "daegu"}


def base_id(item_id: str) -> str:
    return _LANG_SUFFIX.sub("", str(item_id or ""))


def _float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def sido_from_latlng(lat: Any, lng: Any) -> str | None:
    """
    Approximate metro/province from coordinates.
    Prefer this over cross-language address joins (TourAPI contentIds can mismatch).
    """
    la = _float(lat)
    ln = _float(lng)
    if la is None or ln is None:
        return None

    # Jeju
    if 33.05 <= la <= 33.62 and 126.05 <= ln <= 127.0:
        return "jeju"
    # Busan
    if 34.95 <= la <= 35.45 and 128.75 <= ln <= 129.35:
        return "busan"
    # Daegu
    if 35.70 <= la <= 36.05 and 128.40 <= ln <= 128.85:
        return "daegu"
    # Daejeon
    if 36.20 <= la <= 36.50 and 127.20 <= ln <= 127.55:
        return "other"
    # Gwangju
    if 35.05 <= la <= 35.30 and 126.70 <= ln <= 127.05:
        return "other"
    # Incheon (Yeongjong / airport / west coast) — before Seoul
    if 37.25 <= la <= 37.70 and 126.30 <= ln < 126.78:
        return "incheon"
    # Seoul proper
    if 37.42 <= la <= 37.72 and 126.78 <= ln <= 127.20:
        return "seoul"
    # Gyeonggi surrounding the capital
    if 36.85 <= la <= 38.35 and 126.40 <= ln <= 127.95:
        return "gyeonggi"
    return None


def parse_sido(address: str | None) -> str:
    text = address or ""
    for key, pattern in SIDO_RULES:
        if pattern.search(text):
            return key if key in TOP_SIDO else "other"
    return "other"


def parse_district(address: str | None, sido: str | None = None) -> str | None:
    text = address or ""
    m = re.search(r"\b([A-Za-z]+(?:jin)?)-gu\b", text, re.I)
    if m:
        raw = m.group(1).lower()
        return "busanjin" if raw == "busanjin" else raw
    if re.search(r"\bGijang\b|기장군", text, re.I):
        return "gijang"
    if re.search(r"강남구|江南区|カンナム", text):
        return "gangnam"
    if re.search(r"서초구|瑞草区|ソチョ", text):
        return "seocho"
    if re.search(r"종로구|鍾路|钟路|チョンノ|ジョンロ", text):
        return "jongno"
    if re.search(r"마포구|麻浦|マポ", text):
        return "mapo"
    if re.search(r"중구|中区", text) and sido in (None, "seoul", "busan", "incheon"):
        return "jung"
    if re.search(r"부산진구|釜山鎮|釜山镇", text):
        return "busanjin"
    if re.search(r"해운대구|海云台|海雲台|ヘウンデ", text):
        return "haeundae"
    if re.search(r"남구|南区", text) and sido == "busan":
        return "nam"
    if re.search(r"Yeongjong|ヨンジョン|永宗|영종", text, re.I):
        return "yeongjong"
    return None


def parse_region(
    address: str | None,
    lat: Any = None,
    lng: Any = None,
) -> dict:
    """Resolve sido from coordinates first, then address; district from own address."""
    from_coords = sido_from_latlng(lat, lng)
    from_addr = parse_sido(address)
    sido = from_coords or from_addr
    # If address clearly says another metro, trust explicit address over approx bbox edge
    if from_coords and from_addr in TOP_SIDO and from_addr != from_coords:
        # Explicit city name in address wins when it conflicts (edge of bbox)
        if re.search(
            r"Seoul|서울|ソウル|首尔|Busan|부산|釜山|Incheon|인천|仁川|Gyeonggi|경기|京畿|Daegu|대구|大邱",
            address or "",
            re.I,
        ):
            sido = from_addr
        else:
            sido = from_coords
    return {"sido": sido, "district": parse_district(address, sido)}


def enrich_items_with_regions(items: list[dict]) -> None:
    """Attach region from each item's own address + coordinates (no EN twin join)."""
    for item in items:
        item["region"] = parse_region(
            item.get("address"),
            item.get("lat"),
            item.get("lng"),
        )


SEOUL_FEATURED = {"gangnam", "seocho", "jung", "jongno", "mapo"}
BUSAN_FEATURED = {"busanjin", "haeundae", "nam"}


def matches_region_filter(
    region: dict | None,
    sido_filter: str,
    district_filter: str | None = None,
) -> bool:
    """Same rules as app/static/js/regions.js matchesRegionFilter."""
    if not region:
        return sido_filter == "all"
    if sido_filter == "all":
        return True
    if region.get("sido") != sido_filter:
        return False
    if not district_filter or district_filter == "all":
        return True
    featured = (
        SEOUL_FEATURED if sido_filter == "seoul"
        else BUSAN_FEATURED if sido_filter == "busan"
        else None
    )
    if not featured:
        return True
    district = region.get("district")
    if district_filter == "other":
        return not district or district not in featured
    return district == district_filter
