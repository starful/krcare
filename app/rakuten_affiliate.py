"""Rakuten Travel short links for Korea trip prep (krcare)."""

from __future__ import annotations

# Fixed Travelpayouts / Rakuten a.r10.to short links.
RAKUTEN_KOREA_TRAVEL_URL = "https://a.r10.to/hPhGZl"
RAKUTEN_KOREA_ESIM_URL = "https://a.r10.to/h9O1Fq"


def rakuten_korea_hotel_url() -> str:
    """Back-compat alias for Korea travel short link."""
    return RAKUTEN_KOREA_TRAVEL_URL


def rakuten_korea_esim_url() -> str:
    return RAKUTEN_KOREA_ESIM_URL
