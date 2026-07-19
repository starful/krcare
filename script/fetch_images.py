"""
KR Care image fetcher (content-time, once per item).

Priority:
  1. TourAPI `source_image` / `thumb_image` / `org_image` URL in frontmatter
  2. Google Places photo (`GOOGLE_PLACES_API_KEY`) — one fetch, then local/GCS cache
  3. Copy `default.jpg` (brand logo placeholder)

Run via deploy.sh STEP C, or:
  python script/fetch_images.py
  python script/fetch_images.py --missing
  python script/fetch_images.py --limit 30 --force-default
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import time
from pathlib import Path

import frontmatter
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
CONTENT_DIR = BASE_DIR / "app" / "content"
IMAGES_DIR = BASE_DIR / "app" / "static" / "images"

# Places photo fetch: prefer dedicated Places key (Secret Manager: GOOGLE_PLACES_API_KEY)
# Maps JS key alone often returns 403 for places.googleapis.com
PLACES_API_KEY = (
    os.getenv("GOOGLE_PLACES_API_KEY")
    or os.getenv("PLACES_API_KEY")
    or os.getenv("MAPS_API_KEY")
    or os.getenv("GOOGLE_MAPS_API_KEY")
    or os.getenv("KRCAMPUS_GOOGLE_MAPS_API_KEY")
    or ""
).strip()
# Back-compat alias used below
MAPS_API_KEY = PLACES_API_KEY

MAX_WIDTH = 800
PROTECTED = {
    "logo.png",
    "logo.svg",
    "favicon.ico",
    "favicon-32x32.png",
    "favicon-48x48.png",
    "apple-touch-icon.png",
    "android-chrome-192x192.png",
    "android-chrome-512x512.png",
    "default.jpg",
    "default.png",
    "og_image.png",
}

LANG_SUFFIXES = ("_zh_tw", "_en", "_ja", "_zh", "_ko")
PREFERRED_LANG_FILES = ("_en.md", "_ja.md", "_zh.md", "_zh_tw.md", "_ko.md")
HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")
PAREN_KO_RE = re.compile(r"\(([^)]*[\uac00-\ud7a3][^)]*)\)")


def clean_md(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-z]*\n", "", text)
    text = re.sub(r"\n```$", "", text)
    if "---" in text and not text.startswith("---"):
        text = "---" + text.split("---", 1)[1]
    return text


def base_id_from_stem(stem: str) -> str:
    for suffix in LANG_SUFFIXES:
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


def default_image_path() -> Path | None:
    for name in ("default.jpg", "default.png", "logo.png"):
        path = IMAGES_DIR / name
        if path.is_file():
            return path
    return None


def ensure_default_jpg() -> Path | None:
    """Guarantee default.jpg exists (from logo.png if needed)."""
    target = IMAGES_DIR / "default.jpg"
    if target.is_file():
        return target
    logo = IMAGES_DIR / "logo.png"
    if not logo.is_file():
        return None
    try:
        from PIL import Image

        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        src = Image.open(logo).convert("RGBA")
        w, h = 1200, 675
        canvas = Image.new("RGBA", (w, h), (243, 247, 246, 255))
        ratio = min((w * 0.72) / src.width, (h * 0.55) / src.height)
        nw, nh = int(src.width * ratio), int(src.height * ratio)
        resized = src.resize((nw, nh), Image.Resampling.LANCZOS)
        canvas.alpha_composite(resized, ((w - nw) // 2, (h - nh) // 2))
        canvas.convert("RGB").save(target, "JPEG", quality=88, optimize=True)
        print(f"✅ Created default.jpg from logo.png")
        return target
    except Exception as exc:
        print(f"⚠️  Could not create default.jpg: {exc}")
        return None


def iter_primary_items():
    """Yield one metadata dict per base_id (prefer EN file)."""
    if not CONTENT_DIR.is_dir():
        return

    by_base: dict[str, list[Path]] = {}
    for path in sorted(CONTENT_DIR.glob("*.md")):
        if path.name.startswith("."):
            continue
        base = base_id_from_stem(path.stem)
        by_base.setdefault(base, []).append(path)

    for base_id, paths in sorted(by_base.items()):
        chosen = None
        for suffix in PREFERRED_LANG_FILES:
            for path in paths:
                if path.name.endswith(suffix):
                    chosen = path
                    break
            if chosen:
                break
        if not chosen:
            chosen = paths[0]

        try:
            raw = clean_md(chosen.read_text(encoding="utf-8"))
            post = frontmatter.loads(raw)
        except Exception as exc:
            print(f"skip {chosen.name}: {exc}")
            continue

        meta = dict(post.metadata or {})
        yield {
            "base_id": base_id,
            "path": chosen,
            "title": str(meta.get("title") or base_id.replace("_", " ")),
            "lat": meta.get("lat"),
            "lng": meta.get("lng"),
            "address": str(meta.get("address") or ""),
            "source_image": _first_url(
                meta.get("source_image"),
                meta.get("thumb_image"),
                meta.get("org_image"),
                meta.get("tour_thumb"),
            ),
        }


def _first_url(*values) -> str:
    for value in values:
        text = str(value or "").strip()
        if text.startswith("http://") or text.startswith("https://"):
            return text
    return ""


def _parse_float(value) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def download_url(url: str, save_path: Path) -> bool:
    try:
        res = requests.get(
            url,
            timeout=25,
            headers={"User-Agent": "KRCareImageBot/1.0"},
            allow_redirects=True,
        )
        if res.status_code != 200:
            print(f"  TourAPI image HTTP {res.status_code}")
            return False
        ctype = res.headers.get("Content-Type", "")
        if not ctype.startswith("image") and not url.lower().endswith(
            (".jpg", ".jpeg", ".png", ".webp", ".gif")
        ):
            print(f"  TourAPI image unexpected type: {ctype or 'unknown'}")
            return False
        save_path.write_bytes(res.content)
        print(f"  saved TourAPI image ({len(res.content) / 1024:.0f}KB)")
        return True
    except Exception as exc:
        print(f"  TourAPI download error: {exc}")
        return False


def search_places(name: str, lat: float | None, lng: float | None, *, max_results: int = 5) -> list:
    if not MAPS_API_KEY:
        return []
    lang = "ko" if HANGUL_RE.search(name or "") else "en"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": MAPS_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.photos",
    }
    body: dict = {
        "textQuery": name,
        "languageCode": lang,
        "maxResultCount": max_results,
    }
    if lat is not None and lng is not None:
        body["locationBias"] = {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": 2000.0,
            }
        }
    try:
        res = requests.post(
            "https://places.googleapis.com/v1/places:searchText",
            headers=headers,
            json=body,
            timeout=20,
        )
        if res.status_code == 403:
            print("  Places search error: 403 Forbidden (check GOOGLE_PLACES_API_KEY)")
            return []
        res.raise_for_status()
        return res.json().get("places", []) or []
    except Exception as exc:
        print(f"  Places search error: {exc}")
        return []


def pick_place_with_photo(places: list, name: str):
    with_photos = [p for p in places if p.get("photos")]
    if not with_photos:
        return None
    needle = re.sub(r"[^a-z0-9\uac00-\ud7a3]", "", (name or "").lower())
    for place in with_photos:
        display = re.sub(
            r"[^a-z0-9\uac00-\ud7a3]",
            "",
            (place.get("displayName") or {}).get("text", "").lower(),
        )
        if needle and (needle in display or display in needle):
            return place
    return with_photos[0]


def korean_name_from_title(title: str) -> str:
    m = PAREN_KO_RE.search(title or "")
    return (m.group(1).strip() if m else "").strip()


def places_queries(item: dict) -> list[str]:
    title = (item.get("title") or "").strip()
    ko = korean_name_from_title(title)
    plain = re.sub(r"\s*\([^)]*\)\s*", " ", title).strip()
    queries: list[str] = []
    if ko:
        queries.append(ko)
        queries.append(f"{ko} 병원")
    if title:
        queries.append(title)
    if plain and plain not in queries:
        queries.append(plain)
    addr = (item.get("address") or "").strip()
    if ko and addr:
        queries.append(f"{ko} {addr}")
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out


def is_default_placeholder(path: Path) -> bool:
    default = IMAGES_DIR / "default.jpg"
    if not path.is_file() or not default.is_file():
        return False
    try:
        return path.read_bytes() == default.read_bytes()
    except OSError:
        return False


def should_fetch(save_path: Path, *, force: bool, force_default: bool) -> bool:
    if save_path.name in PROTECTED:
        return False
    if force:
        return True
    if not save_path.is_file():
        return True
    if force_default and is_default_placeholder(save_path):
        return True
    return False


def download_places_photo(photo_name: str, save_path: Path) -> bool:
    if not MAPS_API_KEY or not photo_name:
        return False
    url = f"https://places.googleapis.com/v1/{photo_name}/media"
    params = {
        "maxWidthPx": MAX_WIDTH,
        "key": MAPS_API_KEY,
        "skipHttpRedirect": "false",
    }
    try:
        res = requests.get(url, params=params, timeout=25, allow_redirects=True)
        if res.status_code == 200 and res.headers.get("Content-Type", "").startswith("image"):
            save_path.write_bytes(res.content)
            print(f"  saved Places photo ({len(res.content) / 1024:.0f}KB)")
            return True
        print(f"  Places photo HTTP {res.status_code}")
    except Exception as exc:
        print(f"  Places photo error: {exc}")
    return False


def copy_default(save_path: Path) -> bool:
    src = ensure_default_jpg() or default_image_path()
    if not src:
        print("  failed: no default.jpg / logo.png")
        return False
    shutil.copy2(src, save_path)
    print(f"  copied default ← {src.name}")
    return True


def fetch_item(item: dict, *, force: bool = False, force_default: bool = False) -> str:
    base_id = item["base_id"]
    save_path = IMAGES_DIR / f"{base_id}.jpg"
    if save_path.name in PROTECTED:
        return "skip"
    if not should_fetch(save_path, force=force, force_default=force_default):
        return "skip"

    print(f"  title: {item['title']}")

    source = item.get("source_image") or ""
    if source and download_url(source, save_path):
        return "tourapi"

    lat = _parse_float(item.get("lat"))
    lng = _parse_float(item.get("lng"))
    if MAPS_API_KEY:
        for query in places_queries(item):
            place = pick_place_with_photo(search_places(query, lat, lng), query)
            if not place:
                continue
            photos = place.get("photos") or []
            photo_name = (photos[0] or {}).get("name", "")
            label = (place.get("displayName") or {}).get("text", "")
            print(f"  Places match ({query[:40]}): {label}")
            if download_places_photo(photo_name, save_path):
                return "places"
            break
    else:
        print("  Places skipped (GOOGLE_PLACES_API_KEY / MAPS_API_KEY missing)")

    if copy_default(save_path):
        return "default"
    return "fail"


def ensure_missing_placeholders() -> None:
    ensure_default_jpg()
    items = list(iter_primary_items())
    copied = 0
    for item in items:
        path = IMAGES_DIR / f"{item['base_id']}.jpg"
        if path.is_file():
            continue
        if copy_default(path):
            copied += 1
    if copied:
        print(f"📋 Placeholder fill: {copied} file(s)")


def fetch_all_images(
    *,
    only_missing: bool = False,
    force: bool = False,
    force_default: bool = False,
    limit: int = 0,
) -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    ensure_default_jpg()
    items = list(iter_primary_items())
    if only_missing:
        items = [
            item
            for item in items
            if not (IMAGES_DIR / f"{item['base_id']}.jpg").is_file()
            or (force_default and is_default_placeholder(IMAGES_DIR / f"{item['base_id']}.jpg"))
        ]
    if force_default and not force and not only_missing:
        placeholders = [
            item
            for item in items
            if is_default_placeholder(IMAGES_DIR / f"{item['base_id']}.jpg")
            or not (IMAGES_DIR / f"{item['base_id']}.jpg").is_file()
        ]
        if placeholders:
            items = placeholders
    if limit and limit > 0:
        items = items[:limit]

    print(f"\n🖼  Fetching images for {len(items)} item(s)")
    print("   priority: TourAPI source_image → Places (KO name first) → default.jpg\n")

    counts = {"tourapi": 0, "places": 0, "default": 0, "skip": 0, "fail": 0}
    for i, item in enumerate(items, 1):
        print(f"[{i:03d}/{len(items)}] {item['base_id']}")
        result = fetch_item(
            item,
            force=force or only_missing,
            force_default=force_default,
        )
        if result == "skip":
            print("  skip (exists)")
        counts[result] = counts.get(result, 0) + 1
        if result in ("tourapi", "places"):
            time.sleep(0.35)

    ensure_missing_placeholders()
    print("\n" + "─" * 50)
    print(
        "Done — "
        f"tourapi:{counts['tourapi']} places:{counts['places']} "
        f"default:{counts['default']} skip:{counts['skip']} fail:{counts['fail']}"
    )
    print("─" * 50)


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch KR Care clinic images")
    ap.add_argument("--missing", action="store_true", help="Only items without an image file")
    ap.add_argument("--force", action="store_true", help="Overwrite existing images")
    ap.add_argument(
        "--force-default",
        action="store_true",
        help="Overwrite files that are still identical to default.jpg",
    )
    ap.add_argument("--limit", type=int, default=0, help="Max items to process (0=all)")
    args = ap.parse_args()
    fetch_all_images(
        only_missing=args.missing,
        force=args.force,
        force_default=args.force_default,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
