"""Thin Rakuten Travel HGC wrap for Korea hotel search (krcare)."""

from __future__ import annotations

import os
from urllib.parse import quote, quote_plus

RAKUTEN_HGC = os.getenv(
    "RAKUTEN_TRAVEL_HGC", "55b9427b.a63c2df8.55b9427c.3a0d270c"
)
_RAKUTEN_UT = "eyJwYWdlIjoidXJsIiwidHlwZSI6InRleHQiLCJjb2wiOjF9"
KOREA_HOTEL_KEYWORD = "韓国 ホテル"


def rakuten_korea_hotel_url(keyword: str = KOREA_HOTEL_KEYWORD) -> str:
    raw = (
        "https://kw.travel.rakuten.co.jp/keyword/Search.do?"
        + "f_key="
        + quote_plus(keyword)
    )
    pc = quote(raw, safe="")
    return (
        f"https://hb.afl.rakuten.co.jp/hgc/{RAKUTEN_HGC}/"
        f"?pc={pc}&link_type=text&ut={_RAKUTEN_UT}"
    )
