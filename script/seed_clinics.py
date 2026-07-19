#!/usr/bin/env python3
"""Seed clinic markdown files (multilang) from clinic_catalog.CLINIC_SEEDS."""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from clinic_catalog import CLINIC_SEEDS, LANGS, clinic_article  # noqa: E402


def write_clinics(*, force: bool = False) -> int:
    content_dir = ROOT / "app" / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for clinic in CLINIC_SEEDS:
        if clinic.get("skip_seed") and not force:
            # Ensure existing tourapi_clinic keeps region if missing — skip rewrite by default
            continue
        cid = clinic["id"]
        for lang in LANGS:
            path = content_dir / f"{cid}_{lang}.md"
            if path.exists() and not force:
                continue
            path.write_text(clinic_article(lang, clinic), encoding="utf-8")
            written += 1
            print(f"wrote {path.name}")
    return written


def sync_csv() -> None:
    """Rewrite data/items.csv + script/csv/items.csv (generator-compatible Name column)."""
    rows_data = []
    rows_gen = []
    for clinic in CLINIC_SEEDS:
        rows_data.append(
            {
                "Id": clinic["id"],
                "Title": clinic["names"]["en"],
                "Lat": clinic["lat"],
                "Lng": clinic["lng"],
                "Categories": "Clinic",
                "Address": clinic["addresses"]["en"],
                "Website": clinic.get("website") or "",
                "Tel": clinic.get("tel") or "",
                "SourceImage": "",
                "Region": clinic["region"],
            }
        )
        rows_gen.append(
            {
                "Name": clinic["names"]["en"],
                "Id": clinic["id"],
                "Lat": clinic["lat"],
                "Lng": clinic["lng"],
                "Address": clinic["addresses"]["en"],
                "Features": "Clinic",
                "Agoda": "",
                "Website": clinic.get("website") or "",
                "Tel": clinic.get("tel") or "",
                "SourceImage": "",
                "Region": clinic["region"],
            }
        )

    data_path = ROOT / "data" / "items.csv"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    with data_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "Id",
                "Title",
                "Lat",
                "Lng",
                "Categories",
                "Address",
                "Website",
                "Tel",
                "SourceImage",
                "Region",
            ],
        )
        w.writeheader()
        w.writerows(rows_data)
    print(f"synced {data_path} ({len(rows_data)} clinics)")

    gen_path = ROOT / "script" / "csv" / "items.csv"
    gen_path.parent.mkdir(parents=True, exist_ok=True)
    with gen_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "Name",
                "Id",
                "Lat",
                "Lng",
                "Address",
                "Features",
                "Agoda",
                "Website",
                "Tel",
                "SourceImage",
                "Region",
            ],
        )
        w.writeheader()
        w.writerows(rows_gen)
    print(f"synced {gen_path} ({len(rows_gen)} clinics)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed KR Care clinic markdown + CSV")
    ap.add_argument("--force", action="store_true", help="Overwrite existing md files")
    ap.add_argument("--csv-only", action="store_true", help="Only rewrite data/items.csv")
    args = ap.parse_args()
    if not args.csv_only:
        n = write_clinics(force=args.force)
        print(f"seeded {n} markdown files")
    sync_csv()


if __name__ == "__main__":
    main()
