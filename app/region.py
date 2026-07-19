"""Address → region keys for KR Care filters (no paid APIs)."""
from __future__ import annotations

import re

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
    if re.search(r"\bGijang\b", text, re.I):
        return "gijang"
    if re.search(r"강남구", text):
        return "gangnam"
    if re.search(r"서초구", text):
        return "seocho"
    if re.search(r"종로구", text):
        return "jongno"
    if re.search(r"마포구", text):
        return "mapo"
    if re.search(r"중구", text):
        return "jung"
    if re.search(r"부산진구", text):
        return "busanjin"
    if re.search(r"해운대구", text):
        return "haeundae"
    if re.search(r"남구", text) and sido == "busan":
        return "nam"
    return None


def parse_region(address: str | None) -> dict:
    sido = parse_sido(address)
    return {"sido": sido, "district": parse_district(address, sido)}


def enrich_items_with_regions(items: list[dict]) -> None:
    """Attach region from EN address twin when available (stable across UI langs)."""
    en_addr: dict[str, str] = {}
    for item in items:
        if item.get("lang") == "en":
            en_addr[base_id(item.get("id", ""))] = str(item.get("address") or "")

    for item in items:
        bid = base_id(item.get("id", ""))
        address = en_addr.get(bid) or str(item.get("address") or "")
        item["region"] = parse_region(address)
