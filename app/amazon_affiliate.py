"""Amazon JP Associates — content-kind search links (tag=starful06-22)."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote_plus

TAG = os.getenv("AMAZON_JP_TAG", "starful06-22")

# kind → Japanese search keyword + copy (Amazon.co.jp)
_CONTENT: dict[str, dict[str, str]] = {
    "default": {
        "keyword": "韓国旅行 便利グッズ",
        "label_en": "Amazon — Korea travel gear",
        "label_ko": "Amazon — 한국 여행 용품",
        "desc_en": "Handy items for a trip to Korea.",
        "desc_ko": "한국 여행에 편리한 용품.",
    },
    "clinic": {
        "keyword": "旅行用 ポーチ",
        "label_en": "Amazon — travel pouches",
        "label_ko": "Amazon — 여행용 파우치",
        "desc_en": "Pouches and essentials for clinic visits.",
        "desc_ko": "병원 방문용 파우치·필수품.",
    },
    "guide": {
        "keyword": "韓国旅行 グッズ",
        "label_en": "Amazon — Korea trip goods",
        "label_ko": "Amazon — 한국 여행 굿즈",
        "desc_en": "Travel goods to prepare for Korea.",
        "desc_ko": "한국 여행 준비 용품.",
    },
}


def search_url(keyword: str) -> str:
    k = (keyword or "").strip() or _CONTENT["default"]["keyword"]
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
    if key not in _CONTENT:
        key = "default"
    content = _CONTENT[key]
    keyword = content["keyword"]
    is_ko = (lang or "en").lower() in ("ko", "kr")
    return {
        "show_amazon": True,
        "amazon_note": (
            "제휴 광고 · 새 탭에서 열림" if is_ko else "Affiliate ads · opens in new tab"
        ),
        "amazon_cta": {
            "id": "amazon",
            "click_url": search_url(keyword),
            "label": content["label_ko"] if is_ko else content["label_en"],
            "desc": content["desc_ko"] if is_ko else content["desc_en"],
            "keyword": keyword,
        },
    }
