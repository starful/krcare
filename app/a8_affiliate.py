"""A8.net affiliate banners for KR Care.

Agoda Partners + KKday + Korean College. BUYMA removed.
"""

from __future__ import annotations

import os
from typing import Any

_BANNERS: dict[str, dict[str, str]] = {
    "agoda": {
        "id": "agoda",
        "click_url": "",
        "image_url": "",
        "pixel_url": "",
        "label_en": "Agoda — Korea hotels",
        "label_ko": "Agoda — 한국 숙소",
        "desc_en": "Book stays near clinics and treatment areas.",
        "desc_ko": "병원·치료 지역 주변 숙소.",
        "alt_en": "Agoda — hotels",
        "alt_ko": "Agoda — 숙소",
    },
    "kkday": {
        "id": "kkday",
        "click_url": "https://px.a8.net/svt/ejp?a8mat=4BAH9J+4DS29E+52F8+5ZMCH",
        "image_url": "https://www27.a8.net/svt/bgt?aid=260829415265&wid=009&eno=01&mid=s00000023642001006000&mc=1",
        "pixel_url": "https://www16.a8.net/0.gif?a8mat=4BAH9J+4DS29E+52F8+5ZMCH",
        "label_en": "KKday — Korea tours",
        "label_ko": "KKday — 한국 투어",
        "desc_en": "Airport pickup and local experiences.",
        "desc_ko": "공항 픽업·현지 투어.",
        "alt_en": "KKday — affiliate",
        "alt_ko": "KKday — 제휴",
    },
    "korean_college": {
        "id": "korean_college",
        "click_url": "https://px.a8.net/svt/ejp?a8mat=4BAH9J+3ME4FM+51XQ+63OY9",
        "image_url": "https://www29.a8.net/svt/bgt?aid=260829415219&wid=009&eno=01&mid=s00000023579001025000&mc=1",
        "pixel_url": "https://www18.a8.net/0.gif?a8mat=4BAH9J+3ME4FM+51XQ+63OY9",
        "label_en": "Korean College",
        "label_ko": "코리안칼리지",
        "desc_en": "Learn Korean before your visit.",
        "desc_ko": "방문 전 온라인 한국어 수업.",
        "alt_en": "Korean College — affiliate",
        "alt_ko": "코리안칼리지 — 제휴",
    },
}


def _enabled() -> bool:
    return os.getenv("A8_KRCARE_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _copy(
    banner_id: str,
    *,
    lang: str,
    lat: float | None = None,
    lng: float | None = None,
) -> dict[str, str]:
    src = _BANNERS[banner_id]
    is_ko = (lang or "en").lower() == "ko"
    suffix = "ko" if is_ko else "en"
    key = banner_id.upper()
    if banner_id == "agoda":
        try:
            from agoda_partners import url_for_location
        except ImportError:
            from .agoda_partners import url_for_location
        click = url_for_location(
            lang=lang,
            lat=lat,
            lng=lng,
            country="kr",
            default_city=14690,
        )
        return {
            "id": src["id"],
            "click_url": click,
            "image_url": "",
            "pixel_url": "",
            "label": src[f"label_{suffix}"],
            "desc": src[f"desc_{suffix}"],
            "alt": src[f"alt_{suffix}"],
        }
    return {
        "id": src["id"],
        "click_url": os.getenv(f"A8_{key}_CLICK_URL", src["click_url"]),
        "image_url": os.getenv(f"A8_{key}_BANNER_URL", src["image_url"]),
        "pixel_url": os.getenv(f"A8_{key}_PIXEL_URL", src["pixel_url"]),
        "label": src[f"label_{suffix}"],
        "desc": src[f"desc_{suffix}"],
        "alt": src[f"alt_{suffix}"],
    }


def a8_banners_context(
    *,
    lang: str = "en",
    lat: float | None = None,
    lng: float | None = None,
) -> dict[str, Any]:
    if not _enabled():
        return {"show_a8_banners": False, "a8_banners": []}
    is_ko = (lang or "en").lower() == "ko"
    keys = ("agoda", "kkday", "korean_college")
    kw = {"lang": lang, "lat": lat, "lng": lng}
    banners = [_copy(k, **kw) for k in keys]
    return {
        "show_a8_banners": True,
        "a8_banners": banners,
        "a8_banners_title": (
            "한국 방문 제휴" if is_ko else "Korea visit partners"
        ),
        "a8_banners_note": (
            "제휴 광고 · 새 탭에서 열림"
            if is_ko
            else "Affiliate ads · opens in new tab"
        ),
    }
