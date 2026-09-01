"""Which clinic detail pages are indexable (guides + featured districts + rich content)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    import frontmatter
except ImportError:
    frontmatter = None  # type: ignore

from app.region import BUSAN_FEATURED, SEOUL_FEATURED, base_id, parse_region

MIN_INDEXABLE_WORDS = 150
_MDCL_EN = re.compile(r"^mdcl_\d+_en\.md$", re.I)


def body_word_count(text: str) -> int:
    body = (text or "").strip()
    if body.startswith("---") and frontmatter:
        try:
            body = frontmatter.loads(body).content or ""
        except Exception:
            body = body.split("---", 2)[-1]
    elif body.startswith("---"):
        parts = body.split("---", 2)
        body = parts[2] if len(parts) > 2 else ""
    return len(body.split())


def is_indexable_clinic(
    *,
    address: str | None = None,
    lat: Any = None,
    lng: Any = None,
    content: str = "",
) -> bool:
    """Featured Seoul/Busan districts or substantive clinic write-up."""
    if body_word_count(content) >= MIN_INDEXABLE_WORDS:
        return True
    region = parse_region(address, lat, lng)
    sido = region.get("sido")
    district = region.get("district")
    if sido == "seoul" and district in SEOUL_FEATURED:
        return True
    if sido == "busan" and district in BUSAN_FEATURED:
        return True
    return False


def load_indexable_clinic_base_ids(content_dir: Path) -> frozenset[str]:
    """Scan EN clinic markdown once at startup."""
    ids: set[str] = set()
    if not content_dir.is_dir() or not frontmatter:
        return frozenset()
    for path in sorted(content_dir.glob("mdcl_*_en.md")):
        if not _MDCL_EN.match(path.name):
            continue
        try:
            post = frontmatter.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if is_indexable_clinic(
            address=post.get("address"),
            lat=post.get("lat"),
            lng=post.get("lng"),
            content=post.content or "",
        ):
            ids.add(base_id(path.stem))
    return frozenset(ids)
