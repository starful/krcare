"""
Ensure every content item has a local thumbnail JPG for GCS upload.
Copies default.jpg when {base_id}.jpg is missing.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from fetch_images import (
    IMAGES_DIR,
    PROTECTED,
    base_id_from_stem,
    copy_default,
    ensure_default_jpg,
)

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
CONTENT_DIR = BASE_DIR / "app" / "content"


def collect_content_base_ids() -> set[str]:
    ids: set[str] = set()
    if not CONTENT_DIR.is_dir():
        return ids
    for path in CONTENT_DIR.glob("*.md"):
        ids.add(base_id_from_stem(path.stem))
    return ids


def ensure_item_images(*, base_ids: set[str] | None = None) -> dict[str, int]:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    ensure_default_jpg()
    targets = sorted(base_ids if base_ids is not None else collect_content_base_ids())
    copied = skipped = failed = 0

    print(f"\n📋 default placeholder — {len(targets)} base_id(s)\n")
    for base_id in targets:
        filename = f"{base_id}.jpg"
        if filename in PROTECTED:
            continue
        target = IMAGES_DIR / filename
        if target.is_file():
            skipped += 1
            continue
        if copy_default(target):
            copied += 1
        else:
            failed += 1

    print(f"placeholder — copied:{copied} skip:{skipped} fail:{failed}")
    return {"copied": copied, "skipped": skipped, "failed": failed}


if __name__ == "__main__":
    ensure_item_images()
