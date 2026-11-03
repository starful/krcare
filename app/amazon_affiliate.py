"""Amazon JP Associates — content-kind search links (tag=starful06-22)."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote_plus

TAG = os.getenv("AMAZON_JP_TAG", "starful06-22")

# kind → Japanese search keyword (Amazon.co.jp)
_KEYWORDS: dict[str, str] = {
    "default": "韓国旅行 便利グッズ",
    "clinic": "旅行用 ポーチ",
    "guide": "韓国旅行 グッズ",
}

# kind → (label_en, label_ko, desc_en, desc_ko)
_COPY: dict[str, tuple[str, str, str, str]] = {
    "default": (
        "Amazon — Korea travel gear",
        "Amazon — 한국 여행 용품",
        "Handy items for a trip to Korea.",
        "한국 여행에 편리한 용품.",
    ),
    "clinic": (
        "Amazon — travel pouches",
        "Amazon — 여행용 파우치",
        "Pouches and essentials for clinic visits.",
        "병원 방문용 파우치·필수품.",
    ),
    "guide": (
        "Amazon — Korea trip goods",
        "Amazon — 한국 여행 굿즈",
        "Travel goods to prepare for Korea.",
        "한국 여행 준비 용품.",
    ),
}


def search_url(keyword: str) -> str:
    k = (keyword or "").strip() or _KEYWORDS["default"]
    return (
        f"https://www.amazon.co.jp/s?k={quote_plus(k)}"
        f"&tag={TAG}&linkCode=ll2&ref_=as_li_ss_tl"
    )


def _enabled() -> bool:
    return os.getenv("AMAZON_KRCARE_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def amazon_context(*, kind: str = "default", lang: str = "en") -> dict[str, Any]:
    if not _enabled():
        return {"show_amazon": False, "amazon_cta": None, "amazon_note": ""}
    key = (kind or "default").strip().lower() or "default"
    if key not in _KEYWORDS:
        key = "default"
    keyword = _KEYWORDS[key]
    is_ko = (lang or "en").lower() in ("ko", "kr")
    label_en, label_ko, desc_en, desc_ko = _COPY[key]
    return {
        "show_amazon": True,
        "amazon_note": (
            "제휴 광고 · 새 탭에서 열림" if is_ko else "Affiliate ads · opens in new tab"
        ),
        "amazon_cta": {
            "id": "amazon",
            "click_url": search_url(keyword),
            "label": label_ko if is_ko else label_en,
            "desc": desc_ko if is_ko else desc_en,
            "keyword": keyword,
        },
    }
