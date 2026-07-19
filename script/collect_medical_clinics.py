#!/usr/bin/env python3
"""
Collect real KTO medical-tourism clinics from TourAPI (MdclTursmService).

Writes app/content/mdcl_{contentId}_{lang}.md for en/ja/zh/zh_tw.
Removes previous seed clinics (clinic_*) and legacy tourapi_clinic_*.

Usage:
  python3 script/collect_medical_clinics.py
  python3 script/collect_medical_clinics.py --limit 50
  TOURAPI_SERVICE_KEY=... python3 script/collect_medical_clinics.py
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "app" / "content"
CSV_PATH = ROOT / "script" / "csv" / "items.csv"
DATA_CSV = ROOT / "data" / "items.csv"
CACHE_JSON = ROOT / "tmp" / "mdcl_clinics.json"

LANGS = [
    ("en", "ENG"),
    ("ja", "JPN"),
    ("zh", "CHS"),
    ("zh_tw", "CHT"),
]

LIST_URL = "https://apis.data.go.kr/B551011/MdclTursmService/areaBasedList"
DETAIL_URL = "https://apis.data.go.kr/B551011/MdclTursmService/detailCommon"


_KEY_CACHE = ""


def service_key() -> str:
    global _KEY_CACHE
    if _KEY_CACHE:
        return _KEY_CACHE
    key = (
        os.getenv("TOURAPI_SERVICE_KEY")
        or os.getenv("TOUR_API_KEY")
        or os.getenv("DATA_GO_KR_SERVICE_KEY")
        or ""
    ).strip()
    if not key:
        try:
            out = subprocess.check_output(
                [
                    "gcloud",
                    "secrets",
                    "versions",
                    "access",
                    "latest",
                    "--secret=TOURAPI_SERVICE_KEY",
                    "--project=starful-258005",
                ],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            key = out.strip()
        except Exception as exc:
            raise SystemExit(
                f"TOURAPI_SERVICE_KEY missing ({exc}). Set env or gcloud secret."
            ) from exc
    if not key:
        raise SystemExit("TOURAPI_SERVICE_KEY empty")
    _KEY_CACHE = key
    return key


def fetch_json(url: str, params: dict) -> dict:
    sk = urllib.parse.quote(service_key(), safe="")
    qs = "&".join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in params.items())
    full = f"{url}?serviceKey={sk}&{qs}"
    req = urllib.request.Request(full, headers={"User-Agent": "krcare-collect"})
    with urllib.request.urlopen(req, timeout=45) as res:
        return json.loads(res.read().decode())


def items_of(data: dict) -> list[dict]:
    raw = data.get("response", {}).get("body", {}).get("items")
    if not raw or raw == "":
        return []
    item = raw.get("item") if isinstance(raw, dict) else None
    if isinstance(item, dict):
        return [item]
    if isinstance(item, list):
        return item
    return []


def list_all(lang_div: str) -> list[dict]:
    page = 1
    rows = 100
    out: list[dict] = []
    total = None
    while True:
        data = fetch_json(
            LIST_URL,
            {
                "numOfRows": rows,
                "pageNo": page,
                "MobileOS": "ETC",
                "MobileApp": "KRCare",
                "_type": "json",
                "langDivCd": lang_div,
            },
        )
        header = data.get("response", {}).get("header", {})
        if str(header.get("resultCode")) not in ("0", "0000"):
            raise RuntimeError(f"{lang_div} list failed: {header}")
        body = data.get("response", {}).get("body", {})
        if total is None:
            total = int(body.get("totalCount") or 0)
            print(f"  {lang_div} totalCount={total}")
        batch = items_of(data)
        out.extend(batch)
        if not batch or len(out) >= total or page * rows >= total:
            break
        page += 1
        time.sleep(0.12)
    return out


def detail(lang_div: str, content_id: str) -> dict:
    data = fetch_json(
        DETAIL_URL,
        {
            "MobileOS": "ETC",
            "MobileApp": "KRCare",
            "_type": "json",
            "langDivCd": lang_div,
            "contentId": content_id,
        },
    )
    found = items_of(data)
    return found[0] if found else {}


def geo_key(item: dict) -> str:
    try:
        lat = round(float(item.get("mapY") or 0), 5)
        lng = round(float(item.get("mapX") or 0), 5)
    except (TypeError, ValueError):
        return ""
    return f"{lat},{lng}"


def korean_name(title: str) -> str:
    m = re.search(r"\(([^)]*[\uac00-\ud7a3][^)]*)\)", title or "")
    return (m.group(1).strip() if m else "").strip()


def esc(s: str) -> str:
    return str(s or "").replace("\\", "\\\\").replace('"', '\\"')


def address_of(item: dict) -> str:
    base = (item.get("baseAddr") or "").strip()
    detail_addr = (item.get("detailAddr") or "").strip()
    zip_cd = (item.get("zipCd") or "").strip()
    parts = [p for p in (base, detail_addr) if p]
    addr = ", ".join(parts)
    if zip_cd and zip_cd not in addr:
        addr = f"{addr} ({zip_cd})" if addr else zip_cd
    return addr


def website_of(item: dict) -> str:
    return (item.get("homepage") or item.get("homePage") or "").strip()


def tel_of(item: dict) -> str:
    return (item.get("tel") or "").strip()


def image_of(item: dict) -> str:
    return (item.get("orgImage") or item.get("thumbImage") or "").strip()


def summary_for(lang: str, title: str, overview: str) -> str:
    overview = re.sub(r"\s+", " ", (overview or "").strip())
    if overview:
        return overview[:280] + ("…" if len(overview) > 280 else "")
    fallbacks = {
        "en": f"{title} is listed in Korea Tourism Organization medical-tourism OpenAPI. Confirm languages, hours, and booking directly with the clinic.",
        "ja": f"{title}は韓国観光公社の医療ツーリズムOpenAPI掲載情報です。対応言語・診療時間・予約はクリニックへ直接ご確認ください。",
        "zh": f"{title}为韩国旅游发展局医疗观光 OpenAPI 收录信息。请直接向诊所确认语言、时间与预约。",
        "zh_tw": f"{title}為韓國觀光公社醫療觀光 OpenAPI 收錄資訊。請直接向診所確認語言、時間與預約。",
    }
    return fallbacks.get(lang, fallbacks["en"])


def body_for(lang: str, title: str, address: str, tel: str, website: str, overview: str) -> str:
    overview = (overview or "").strip() or summary_for(lang, title, "")
    details = {
        "en": f"""## Overview

{overview}

## Listed details

- **Phone:** {tel or "Confirm with clinic"}
- **Address:** {address or "Confirm with clinic"}
- **Website:** {website or "Ask the clinic"}
- **Source:** Korea Tourism Organization medical tourism OpenAPI (MdclTursmService)

## Before you book

KR Care lists public KTO medical-tourism data. We do **not** verify prices, outcomes, or doctor credentials beyond the listing.

Ask the clinic directly about languages, hours, deposits/cancellations, and what to bring.
""",
        "ja": f"""## Overview

{overview}

## Listed details

- **電話:** {tel or "クリニックへ確認"}
- **住所:** {address or "クリニックへ確認"}
- **Website:** {website or "クリニックへ確認"}
- **出典:** 韓国観光公社 医療ツーリズム OpenAPI (MdclTursmService)

## Before you book

公開掲載情報以上の料金・効果・資格は保証しません。対応言語・時間・予約条件は直接ご確認ください。
""",
        "zh": f"""## Overview

{overview}

## Listed details

- **电话:** {tel or "请向诊所确认"}
- **地址:** {address or "请向诊所确认"}
- **Website:** {website or "请向诊所确认"}
- **来源:** 韩国旅游发展局医疗观光 OpenAPI (MdclTursmService)

## Before you book

我们不保证超出公开信息的价格、疗效或资质。请直接向诊所确认语言、时间与预约规则。
""",
        "zh_tw": f"""## Overview

{overview}

## Listed details

- **電話:** {tel or "請向診所確認"}
- **地址:** {address or "請向診所確認"}
- **Website:** {website or "請向診所確認"}
- **來源:** 韓國觀光公社醫療觀光 OpenAPI (MdclTursmService)

## Before you book

我們不保證超出公開資訊的價格、療效或資格。請直接向診所確認語言、時間與預約規則。
""",
    }
    return details[lang]


def clear_old_content() -> int:
    removed = 0
    for path in CONTENT_DIR.glob("*.md"):
        name = path.name
        if name.startswith("clinic_") or name.startswith("tourapi_clinic_"):
            path.unlink()
            removed += 1
    # also remove previous mdcl_* for clean rebuild
    for path in CONTENT_DIR.glob("mdcl_*.md"):
        path.unlink()
        removed += 1
    return removed


def write_md(base_id: str, lang: str, item: dict, overview: str) -> Path:
    title = (item.get("title") or base_id).strip()
    lat = item.get("mapY") or "0"
    lng = item.get("mapX") or "0"
    address = address_of(item)
    website = website_of(item)
    tel = tel_of(item)
    source_image = image_of(item)
    thumb = f"/static/images/{base_id}.jpg"
    today = date.today().isoformat()
    summary = summary_for(lang, title, overview)
    body = body_for(lang, title, address, tel, website, overview)
    text = f"""---
lang: {lang}
title: "{esc(title)}"
lat: {lat}
lng: {lng}
categories: ["Clinic"]
thumbnail: "{thumb}"
address: "{esc(address)}"
date: "{today}"
agoda: ""
website: "{esc(website)}"
tel: "{esc(tel)}"
source_image: "{esc(source_image)}"
summary: "{esc(summary)}"
image_prompt: ""
content_id: "{esc(item.get('contentId'))}"
source: "MdclTursmService"
---

{body}
"""
    path = CONTENT_DIR / f"{base_id}_{lang}.md"
    path.write_text(text, encoding="utf-8")
    return path


def sync_csv(eng_items: list[dict]) -> None:
    rows = []
    for it in eng_items:
        cid = str(it.get("contentId") or "").strip()
        if not cid:
            continue
        rows.append(
            {
                "Name": it.get("title") or "",
                "Id": f"mdcl_{cid}",
                "Lat": it.get("mapY") or "",
                "Lng": it.get("mapX") or "",
                "Address": address_of(it),
                "Features": "Clinic",
                "Agoda": "",
                "Website": website_of(it),
                "Tel": tel_of(it),
                "SourceImage": image_of(it),
                "Region": "",
            }
        )
    fieldnames = [
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
    ]
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    DATA_CSV.parent.mkdir(parents=True, exist_ok=True)
    with DATA_CSV.open("w", encoding="utf-8", newline="") as f:
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
        for r in rows:
            w.writerow(
                {
                    "Id": r["Id"],
                    "Title": r["Name"],
                    "Lat": r["Lat"],
                    "Lng": r["Lng"],
                    "Categories": "Clinic",
                    "Address": r["Address"],
                    "Website": r["Website"],
                    "Tel": r["Tel"],
                    "SourceImage": r["SourceImage"],
                    "Region": "",
                }
            )
    print(f"synced CSV ({len(rows)} clinics)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="Max ENG clinics (0=all)")
    ap.add_argument("--skip-detail", action="store_true", help="Skip detailCommon overview fetch")
    args = ap.parse_args()

    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    print("Fetching TourAPI medical lists…")
    by_lang: dict[str, list[dict]] = {}
    for lang, div in LANGS:
        by_lang[lang] = list_all(div)
        time.sleep(0.2)

    eng = by_lang["en"]
    if args.limit and args.limit > 0:
        eng = eng[: args.limit]

    # Index other langs by geo + korean name
    indexes: dict[str, dict[str, dict]] = {}
    for lang, items in by_lang.items():
        if lang == "en":
            continue
        geo: dict[str, dict] = {}
        ko: dict[str, dict] = {}
        for it in items:
            gk = geo_key(it)
            if gk and gk not in geo:
                geo[gk] = it
            kn = korean_name(it.get("title") or "")
            if kn and kn not in ko:
                ko[kn] = it
        indexes[lang] = {"geo": geo, "ko": ko}

    removed = clear_old_content()
    print(f"removed {removed} old markdown files")

    written = 0
    catalog = []
    for i, base in enumerate(eng, 1):
        cid = str(base.get("contentId") or "").strip()
        if not cid:
            continue
        base_id = f"mdcl_{cid}"
        kn = korean_name(base.get("title") or "")
        gk = geo_key(base)

        # Enrich ENG with detail (overview/homepage/tel/images when present)
        if not args.skip_detail:
            try:
                d = detail("ENG", cid)
                if d:
                    for k in ("overview", "homepage", "tel", "orgImage", "thumbImage", "baseAddr", "detailAddr", "zipCd"):
                        if d.get(k) and not base.get(k):
                            base[k] = d[k]
                time.sleep(0.08)
            except Exception as exc:
                print(f"  detail fail {cid}: {exc}")

        overview_en = (base.get("overview") or "").strip()
        write_md(base_id, "en", base, overview_en)
        written += 1

        for lang, div in LANGS:
            if lang == "en":
                continue
            matched = None
            idx = indexes.get(lang) or {}
            if kn and kn in (idx.get("ko") or {}):
                matched = idx["ko"][kn]
            elif gk and gk in (idx.get("geo") or {}):
                matched = idx["geo"][gk]
            if not matched:
                # fallback: use ENG record with same coords (title stays ENG — better than missing lang file)
                matched = dict(base)
            overview = ""
            if not args.skip_detail and matched.get("contentId") and matched.get("contentId") != cid:
                try:
                    d = detail(div, str(matched["contentId"]))
                    if d:
                        overview = (d.get("overview") or "").strip()
                        for k in ("homepage", "tel", "orgImage", "thumbImage", "baseAddr", "detailAddr", "zipCd", "title"):
                            if d.get(k) and not matched.get(k):
                                matched[k] = d[k]
                    time.sleep(0.05)
                except Exception:
                    pass
            if not overview:
                overview = overview_en
            write_md(base_id, lang, matched, overview)
            written += 1

        catalog.append(
            {
                "id": base_id,
                "content_id": cid,
                "title": base.get("title"),
                "lat": float(base.get("mapY") or 0),
                "lng": float(base.get("mapX") or 0),
                "address": address_of(base),
                "website": website_of(base),
                "tel": tel_of(base),
                "source_image": image_of(base),
                "korean_name": kn,
            }
        )
        if i % 25 == 0:
            print(f"  wrote {i}/{len(eng)} clinics…")

    CACHE_JSON.parent.mkdir(parents=True, exist_ok=True)
    CACHE_JSON.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sync_csv(eng)
    print(f"done: {len(eng)} clinics, {written} markdown files → {CONTENT_DIR}")
    print(f"catalog: {CACHE_JSON}")


if __name__ == "__main__":
    main()
