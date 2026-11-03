"""Affiliate banners for KR Care.

Agoda Partners only (A8 KKday / Korean College removed).
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


def a8_banners_context(
    *,
    lang: str = "en",
    lat: float | None = None,
    lng: float | None = None,
) -> dict[str, Any]:
    if not _enabled():
        return {
            "show_a8_banners": False,
            "a8_banners": [],
            "agoda_cta": None,
            "show_agoda_cta": False,
        }
    is_ko = (lang or "en").lower() == "ko"
    keys = ("agoda",)
    kw = {"lang": lang, "lat": lat, "lng": lng}
    banners = [_copy(k, **kw) for k in keys]
    agoda = next((b for b in banners if b.get("id") == "agoda"), None)
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
        "agoda_cta": agoda,
        "show_agoda_cta": agoda is not None,
    }
