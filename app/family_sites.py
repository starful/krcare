"""OK Series cross-site link registry (copy into each app's family_sites.py)."""

from __future__ import annotations

from typing import Any

OK_SERIES_IDS = frozenset({"okramen", "okonsen", "okcaddie"})
CAMPUS_IDS = frozenset({"jpcampus", "krcampus"})
KR_SERIES_IDS = frozenset({"krcampus", "krcare"})
STANDALONE_IDS = frozenset({"statfacts", "starful.biz"})

SITE_REGISTRY: list[dict[str, Any]] = [
    {
        "id": "okramen",
        "url": "https://okramen.net",
        "emoji": "🍜",
        "name": "OK Ramen",
        "desc_en": "Japan Ramen Guide",
        "desc_ko": "일본 라멘 맛집 가이드",
        "desc_ja": "日本ラーメンガイド",
    },
    {
        "id": "okonsen",
        "url": "https://okonsen.net",
        "emoji": "♨️",
        "name": "OK Onsen",
        "desc_en": "Onsen & Ryokan Guide",
        "desc_ko": "온천 & 료칸 완벽 가이드",
        "desc_ja": "温泉・旅館ガイド",
    },
    {
        "id": "okcaddie",
        "url": "https://okcaddie.net",
        "emoji": "⛳",
        "name": "OKCaddie",
        "desc_en": "Japan Golf Course Map",
        "desc_ko": "일본 골프장 지도 & 가이드",
        "desc_ja": "日本ゴルフ場マップ",
    },
    {
        "id": "jpcampus",
        "url": "https://jpcampus.net",
        "emoji": "🏫",
        "name": "JP Campus",
        "desc_en": "Japan Study & School Map",
        "desc_ko": "일본 유학·학교 찾기",
        "desc_ja": "日本留学・学校マップ",
    },
    {
        "id": "krcampus",
        "url": "https://krcampus.net",
        "emoji": "🇰🇷",
        "name": "KR Campus",
        "desc_en": "Study in Korea Guides",
        "desc_ko": "한국 유학 실전 가이드",
        "desc_ja": "韓国留学ガイド",
    },
    {
        "id": "krcare",
        "url": "https://krcare.net",
        "emoji": "💚",
        "name": "KR Care",
        "desc_en": "Korea medical trip care",
        "desc_ko": "한국 의료여행 케어",
        "desc_ja": "韓国メディカル旅行ケア",
    },
]

_SITES_BY_ID = {site["id"]: site for site in SITE_REGISTRY}

# Footer: OK Series ↔ OK Series only; campus ↔ campus only.
FOOTER_GROUPS: dict[str, list[str]] = {
    "okramen": ["okonsen", "okcaddie"],
    "okonsen": ["okramen", "okcaddie"],
    "okcaddie": ["okramen", "okonsen"],
    "jpcampus": ["krcampus"],
    "krcampus": ["jpcampus", "krcare"],
    "krcare": ["krcampus"],
}

# Region contextual links — OK Series sites only (no campus / statfacts / starful).
REGION_CROSS_LINKS: dict[str, list[dict[str, str]]] = {
    "kyoto": [
        {
            "id": "okonsen",
            "url_en": "https://okonsen.net/",
            "url_ko": "https://okonsen.net/?lang=ko",
            "label_en": "Onsen & ryokan near Kyoto",
            "label_ko": "교토 근처 온천·료칸 가이드",
        },
        {
            "id": "okramen",
            "url_en": "https://okramen.net/",
            "url_ko": "https://okramen.net/?lang=ko",
            "label_en": "Kyoto ramen on the map",
            "label_ko": "교토 라멘 맛집 지도",
        },
    ],
    "tokyo": [
        {
            "id": "okramen",
            "url_en": "https://okramen.net/",
            "url_ko": "https://okramen.net/?lang=ko",
            "label_en": "Tokyo ramen shops on the map",
            "label_ko": "도쿄 라멘 맛집 지도",
        },
        {
            "id": "okonsen",
            "url_en": "https://okonsen.net/",
            "url_ko": "https://okonsen.net/?lang=ko",
            "label_en": "Onsen & ryokan near Tokyo",
            "label_ko": "도쿄 근처 온천·료칸",
        },
    ],
    "hakone": [
        {
            "id": "okonsen",
            "url_en": "https://okonsen.net/",
            "url_ko": "https://okonsen.net/?lang=ko",
            "label_en": "Hakone onsen & ryokan picks",
            "label_ko": "하코네 온천·료칸 추천",
        },
        {
            "id": "okcaddie",
            "url_en": "https://okcaddie.net/course/hakone_country_club",
            "url_ko": "https://okcaddie.net/course/hakone_country_club?lang=ko",
            "label_en": "Golf near Hakone",
            "label_ko": "하코네 근처 골프장",
        },
    ],
    "okinawa": [
        {
            "id": "okcaddie",
            "url_en": "https://okcaddie.net/",
            "url_ko": "https://okcaddie.net/?lang=ko",
            "label_en": "Okinawa golf courses",
            "label_ko": "오키나와 골프장 지도",
        },
        {
            "id": "okonsen",
            "url_en": "https://okonsen.net/",
            "url_ko": "https://okonsen.net/?lang=ko",
            "label_en": "Ryokan stays in Okinawa",
            "label_ko": "오키나와 료칸·숙소",
        },
    ],
    "hokkaido": [
        {
            "id": "okramen",
            "url_en": "https://okramen.net/",
            "url_ko": "https://okramen.net/?lang=ko",
            "label_en": "Hokkaido ramen guide",
            "label_ko": "홋카이도 라멘 가이드",
        },
        {
            "id": "okonsen",
            "url_en": "https://okonsen.net/",
            "url_ko": "https://okonsen.net/?lang=ko",
            "label_en": "Hokkaido onsen & ryokan",
            "label_ko": "홋카이도 온천·료칸",
        },
    ],
    "osaka": [
        {
            "id": "okramen",
            "url_en": "https://okramen.net/",
            "url_ko": "https://okramen.net/?lang=ko",
            "label_en": "Osaka ramen on the map",
            "label_ko": "오사카 라멘 지도",
        },
        {
            "id": "okonsen",
            "url_en": "https://okonsen.net/",
            "url_ko": "https://okonsen.net/?lang=ko",
            "label_en": "Onsen & ryokan near Osaka",
            "label_ko": "오사카 근처 온천·료칸",
        },
    ],
    "fukuoka": [
        {
            "id": "okramen",
            "url_en": "https://okramen.net/",
            "url_ko": "https://okramen.net/?lang=ko",
            "label_en": "Fukuoka tonkotsu ramen guide",
            "label_ko": "후쿠오카 돈코츠 라멘",
        },
        {
            "id": "okcaddie",
            "url_en": "https://okcaddie.net/",
            "url_ko": "https://okcaddie.net/?lang=ko",
            "label_en": "Kyushu golf courses",
            "label_ko": "규슈 골프장 지도",
        },
    ],
    "beppu": [
        {
            "id": "okonsen",
            "url_en": "https://okonsen.net/",
            "url_ko": "https://okonsen.net/?lang=ko",
            "label_en": "Beppu onsen & ryokan",
            "label_ko": "벳푸 온천·료칸",
        },
        {
            "id": "okramen",
            "url_en": "https://okramen.net/",
            "url_ko": "https://okramen.net/?lang=ko",
            "label_en": "Ramen near Beppu",
            "label_ko": "벳푸 근처 라멘",
        },
    ],
}


def _allowed_sibling_ids(current_id: str) -> frozenset[str]:
    if current_id in OK_SERIES_IDS:
        return OK_SERIES_IDS
    if current_id == "krcare":
        return KR_SERIES_IDS
    if current_id in CAMPUS_IDS:
        return CAMPUS_IDS | frozenset({"krcare"})
    return frozenset()


def normalize_lang(lang: str | None) -> str:
    if not lang:
        return "en"
    lang = lang.strip().lower()
    if lang in ("ko", "kr"):
        return "ko"
    if lang == "ja":
        return "ja"
    return "en"


def site_home_url(site_id: str, lang: str) -> str:
    site = _SITES_BY_ID.get(site_id)
    if not site:
        return "/"
    base = site["url"].rstrip("/")
    if site_id == "jpcampus" and lang == "ko":
        return f"{base}/?lang=kr"
    if site_id == "krcampus" and lang == "ja":
        return f"{base}/?lang=ja"
    if lang == "ko" and site_id in OK_SERIES_IDS:
        return f"{base}/?lang=ko"
    return f"{base}/"


def site_description(site: dict[str, Any], lang: str) -> str:
    if lang == "ja" and site.get("desc_ja"):
        return site["desc_ja"]
    if lang == "ko" and site.get("desc_ko"):
        return site["desc_ko"]
    return site.get("desc_en", site["name"])


def family_sites_for(current_id: str, lang: str | None = "en") -> list[dict[str, str]]:
    if current_id in STANDALONE_IDS:
        return []
    lang = normalize_lang(lang)
    order = FOOTER_GROUPS.get(current_id, [])
    results: list[dict[str, str]] = []
    for site_id in order:
        if site_id == current_id:
            continue
        site = _SITES_BY_ID.get(site_id)
        if not site:
            continue
        results.append(
            {
                "id": site_id,
                "url": site_home_url(site_id, lang),
                "emoji": site["emoji"],
                "name": site["name"],
                "desc": site_description(site, lang),
            }
        )
    return results


def family_section_title(lang: str | None, variant: str = "japan") -> str:
    lang = normalize_lang(lang)
    if variant == "study":
        if lang == "ja":
            return "留学ガイドをもっと見る"
        if lang == "ko":
            return "유학 가이드 더 보기"
        return "Explore Study Abroad Guides"
    if lang == "ko":
        return "일본 여행 더 알아보기"
    if lang == "ja":
        return "日本旅行をもっと見る"
    return "Explore More of Japan"


def family_section_variant(current_id: str) -> str:
    if current_id in CAMPUS_IDS or current_id in KR_SERIES_IDS:
        return "study"
    return "japan"


def parse_region(address: str | None) -> str | None:
    if not address:
        return None
    first = address.split(",")[0].strip().lower()
    if not first:
        return None
    for key in REGION_CROSS_LINKS:
        if key in first or first in key:
            return key
    for token in address.lower().replace(",", " ").split():
        token = token.strip()
        if token in REGION_CROSS_LINKS:
            return token
    return None


def _pick_label(entry: dict[str, str], lang: str) -> str:
    if lang == "ko":
        return entry.get("label_ko") or entry["label_en"]
    return entry["label_en"]


def _pick_url(entry: dict[str, str], lang: str) -> str:
    if lang == "ko":
        return entry.get("url_ko") or entry["url_en"]
    return entry["url_en"]


def cross_links_for(
    current_id: str,
    lang: str | None = "en",
    *,
    address: str | None = None,
    categories: list[str] | None = None,
) -> list[dict[str, str]]:
    if current_id in STANDALONE_IDS:
        return []

    lang = normalize_lang(lang)
    allowed = _allowed_sibling_ids(current_id)
    if not allowed:
        return []

    links: list[dict[str, str]] = []

    # OK Series only: region-based contextual links.
    if current_id in OK_SERIES_IDS:
        region = parse_region(address)
        if region:
            for entry in REGION_CROSS_LINKS[region]:
                if entry["id"] == current_id or entry["id"] not in allowed:
                    continue
                site = _SITES_BY_ID.get(entry["id"], {})
                links.append(
                    {
                        "id": entry["id"],
                        "url": _pick_url(entry, lang),
                        "emoji": site.get("emoji", "🔗"),
                        "label": _pick_label(entry, lang),
                    }
                )

    if not links:
        for site in family_sites_for(current_id, lang):
            links.append(
                {
                    "id": site["id"],
                    "url": site["url"],
                    "emoji": site["emoji"],
                    "label": site["desc"],
                }
            )
            if len(links) >= 2:
                break

    # Campus cluster: partner site only on detail pages.
    if current_id == "jpcampus":
        partner = _SITES_BY_ID["krcampus"]
        partner_link = {
            "id": "krcampus",
            "url": site_home_url("krcampus", lang),
            "emoji": partner["emoji"],
            "label": site_description(partner, lang),
        }
        links = [partner_link]
    elif current_id == "krcampus":
        partner = _SITES_BY_ID["jpcampus"]
        partner_link = {
            "id": "jpcampus",
            "url": site_home_url("jpcampus", lang),
            "emoji": partner["emoji"],
            "label": site_description(partner, lang),
        }
        links = [partner_link]

    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for link in links:
        if link["id"] in seen:
            continue
        seen.add(link["id"])
        deduped.append(link)
    return deduped[:3]


def inject_family_context(current_id: str, lang: str | None = "en") -> dict[str, Any]:
    if current_id in STANDALONE_IDS:
        return {
            "family_sites": [],
            "family_section_title": "",
            "family_lang": normalize_lang(lang),
        }
    lang = normalize_lang(lang)
    variant = family_section_variant(current_id)
    return {
        "family_sites": family_sites_for(current_id, lang),
        "family_section_title": family_section_title(lang, variant),
        "family_lang": lang,
    }
