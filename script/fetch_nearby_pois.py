#!/usr/bin/env python3
"""
Fetch / cache Stay & Food POIs near clinics into app/static/json/nearby_pois.json.

Clinic sources (first available):
  1. tmp/mdcl_clinics.json (from collect_medical_clinics.py)
  2. clinic_catalog.CLINIC_SEEDS (legacy)

Usage:
  python script/fetch_nearby_pois.py
  python script/fetch_nearby_pois.py --limit 80 --stay 2 --food 2
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from clinic_catalog import CLINIC_SEEDS, LANGS, build_nearby_for_clinic, offset_latlng, stable_id  # noqa: E402

OUT = ROOT / "app" / "static" / "json" / "nearby_pois.json"
CATALOG = ROOT / "tmp" / "mdcl_clinics.json"


def load_existing() -> list[dict]:
    if not OUT.exists():
        return []
    try:
        data = json.loads(OUT.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            pois = data.get("pois")
            return pois if isinstance(pois, list) else []
        return []
    except Exception:
        return []


def write_payload(pois: list[dict]) -> None:
    payload = {
        "anchor": {},
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "pois": pois,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def merge_pois(existing: list[dict], incoming: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {str(p.get("id")): p for p in existing if p.get("id")}
    for poi in incoming:
        pid = str(poi.get("id") or "")
        if not pid:
            continue
        if pid not in by_id:
            by_id[pid] = poi
            continue
        old = by_id[pid]
        old_clinics = set(old.get("near_clinics") or [])
        new_clinics = set(poi.get("near_clinics") or [])
        old["near_clinics"] = sorted(old_clinics | new_clinics)
        for key in ("tel", "website", "thumbnail", "region", "kind", "lat", "lng", "source"):
            if not old.get(key) and poi.get(key):
                old[key] = poi[key]
        if isinstance(poi.get("i18n"), dict):
            old_i18n = old.setdefault("i18n", {})
            for lang, block in poi["i18n"].items():
                if lang not in old_i18n:
                    old_i18n[lang] = block
    return list(by_id.values())


def clinics_from_catalog() -> list[dict]:
    if not CATALOG.exists():
        return []
    raw = json.loads(CATALOG.read_text(encoding="utf-8"))
    out = []
    for row in raw:
        title = row.get("title") or row.get("id")
        names = {lang: title for lang in LANGS}
        addr = row.get("address") or ""
        addresses = {lang: addr for lang in LANGS}
        out.append(
            {
                "id": row["id"],
                "region": row.get("region") or "korea",
                "names": names,
                "lat": float(row.get("lat") or 0),
                "lng": float(row.get("lng") or 0),
                "addresses": addresses,
                "website": row.get("website") or "",
                "tel": row.get("tel") or "",
                "focus": "medical tourism listing",
            }
        )
    return out


def clinics_to_process(clinic_id: str | None, limit: int) -> list[dict]:
    clinics = clinics_from_catalog() or list(CLINIC_SEEDS)
    if clinic_id:
        found = [c for c in clinics if c["id"] == clinic_id]
        if not found:
            raise SystemExit(f"Unknown clinic id: {clinic_id}")
        return found
    if limit and limit > 0:
        return clinics[:limit]
    return clinics


def main() -> None:
    ap = argparse.ArgumentParser(description="Cache nearby Stay/Food POIs for KR Care clinics")
    ap.add_argument("--clinic", default="", help="Only one clinic id")
    ap.add_argument("--limit", type=int, default=0, help="Max clinics (0=all)")
    ap.add_argument("--stay", type=int, default=2, help="Stay POIs per clinic")
    ap.add_argument("--food", type=int, default=2, help="Food POIs per clinic")
    ap.add_argument("--replace", action="store_true", help="Replace file instead of merge")
    args = ap.parse_args()

    clinics = clinics_to_process(args.clinic or None, args.limit)
    incoming: list[dict] = []
    for clinic in clinics:
        batch = build_nearby_for_clinic(clinic, stay_n=args.stay, food_n=args.food)
        incoming.extend(batch)
        print(f"{clinic['id']}: +{len(batch)} POIs")

    if args.replace:
        merged = incoming
    else:
        processed = {c["id"] for c in clinics}
        keep = []
        for p in load_existing():
            if p.get("source") == "seed_nearby":
                near = set(p.get("near_clinics") or [])
                if near & processed:
                    continue
            keep.append(p)
        merged = merge_pois(keep, incoming)

    write_payload(merged)
    stays = sum(1 for p in merged if p.get("kind") == "Stay")
    foods = sum(1 for p in merged if p.get("kind") == "Food")
    print(f"wrote {OUT} → {len(merged)} POIs ({stays} Stay, {foods} Food)")


if __name__ == "__main__":
    main()
