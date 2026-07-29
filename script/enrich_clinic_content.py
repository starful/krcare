#!/usr/bin/env python3
"""
Enrich all mdcl_* clinic markdown with TourAPI detail + travel sections.

- Fetches detailCommon (TourAPI only — no Places / Gemini)
- Fills overview / tel / website when present
- Always writes Listed / Before / Checklist / Getting there / Nearby cards
- Empty tel/website/address use localized "not in public listing" placeholders
- Nearby: up to 3 Stay/Food from nearby_pois.json (near_clinics)

Usage:
  python3 script/enrich_clinic_content.py
  python3 script/enrich_clinic_content.py --limit 10
  python3 script/enrich_clinic_content.py --skip-api   # sections only, no TourAPI
"""
from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import date
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "app" / "content"
NEARBY_FILE = ROOT / "app" / "static" / "json" / "nearby_pois.json"
DETAIL_URL = "https://apis.data.go.kr/B551011/MdclTursmService/detailCommon"

LANG_DIV = {"en": "ENG", "ja": "JPN", "zh": "CHS", "zh_tw": "CHT"}
LANGS = ("en", "ja", "zh", "zh_tw")

NA = {
    "en": "Not in public listing — ask the clinic",
    "ja": "公開情報なし — クリニックへ確認",
    "zh": "公开信息未收录 — 请向诊所确认",
    "zh_tw": "公開資訊未收錄 — 請向診所確認",
}

SOURCE = {
    "en": "Korea Tourism Organization medical tourism OpenAPI (MdclTursmService)",
    "ja": "韓国観光公社 医療ツーリズム OpenAPI (MdclTursmService)",
    "zh": "韩国旅游发展局医疗观光 OpenAPI (MdclTursmService)",
    "zh_tw": "韓國觀光公社醫療觀光 OpenAPI (MdclTursmService)",
}

LABELS = {
    "en": {
        "phone": "Phone",
        "address": "Address",
        "website": "Website",
        "source": "Source",
        "overview_empty": "No public overview in KTO data — ask the clinic for languages, hours, and booking.",
    },
    "ja": {
        "phone": "電話",
        "address": "住所",
        "website": "Website",
        "source": "出典",
        "overview_empty": "公開の紹介文がありません。対応言語・時間・予約はクリニックへご確認ください。",
    },
    "zh": {
        "phone": "电话",
        "address": "地址",
        "website": "Website",
        "source": "来源",
        "overview_empty": "公开数据中暂无介绍。语言、时间与预约请向诊所确认。",
    },
    "zh_tw": {
        "phone": "電話",
        "address": "地址",
        "website": "Website",
        "source": "來源",
        "overview_empty": "公開資料中暫無介紹。語言、時間與預約請向診所確認。",
    },
}

_KEY = ""


def service_key() -> str:
    global _KEY
    if _KEY:
        return _KEY
    key = (
        os.getenv("TOURAPI_SERVICE_KEY")
        or os.getenv("TOUR_API_KEY")
        or os.getenv("DATA_GO_KR_SERVICE_KEY")
        or ""
    ).strip()
    if not key:
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
    if not key:
        raise SystemExit("TOURAPI_SERVICE_KEY missing")
    _KEY = key
    return key


def fetch_json(params: dict, retries: int = 10) -> dict:
    sk = urllib.parse.quote(service_key(), safe="")
    qs = "&".join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in params.items())
    url = f"{DETAIL_URL}?serviceKey={sk}&{qs}"
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": "krcare-enrich"}),
                timeout=45,
            ) as r:
                return json.loads(r.read().decode())
        except Exception as exc:
            last_exc = exc
            msg = str(exc)
            if "429" in msg or "Too Many" in msg:
                wait = min(60.0, 5.0 * (1.6 ** attempt))
                print(f"  rate-limited, sleep {wait:.0f}s (attempt {attempt+1}/{retries})", flush=True)
                time.sleep(wait)
                continue
            if attempt < retries - 1:
                time.sleep(1.2)
                continue
            raise
    raise last_exc or RuntimeError("fetch_json failed")


def first_item(data: dict) -> dict:
    items = data.get("response", {}).get("body", {}).get("items")
    if not items or items == "":
        return {}
    item = items.get("item") if isinstance(items, dict) else items
    if isinstance(item, list):
        return item[0] if item else {}
    return item or {}


def clean_html(s: str) -> str:
    if not s:
        return ""
    s = html.unescape(s)
    s = s.replace("<br />", "\n").replace("<br/>", "\n").replace("<br>", "\n")
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def address_of(item: dict) -> str:
    base = (item.get("baseAddr") or "").strip()
    detail = (item.get("detailAddr") or "").strip()
    zip_cd = (item.get("zipCd") or "").strip()
    parts = [p for p in (base, detail) if p]
    addr = ", ".join(parts)
    if zip_cd and zip_cd not in addr:
        addr = f"{addr} ({zip_cd})" if addr else zip_cd
    return addr


def esc(s: str) -> str:
    return str(s or "").replace("\\", "\\\\").replace('"', '\\"')


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * 6371000 * asin(sqrt(a))


def load_nearby_index() -> dict[str, list[dict]]:
    if not NEARBY_FILE.exists():
        return {}
    raw = json.loads(NEARBY_FILE.read_text(encoding="utf-8"))
    pois = raw.get("pois") if isinstance(raw, dict) else raw
    idx: dict[str, list[dict]] = {}
    for poi in pois or []:
        for cid in poi.get("near_clinics") or []:
            idx.setdefault(str(cid), []).append(poi)
    return idx


def pick_nearby(pois: list[dict], lat: float, lng: float, n: int = 3) -> list[dict]:
    if not pois:
        return []

    def dist(p: dict) -> float:
        try:
            return haversine_m(lat, lng, float(p["lat"]), float(p["lng"]))
        except (TypeError, ValueError, KeyError):
            return 1e12

    stays = sorted([p for p in pois if p.get("kind") == "Stay"], key=dist)
    foods = sorted([p for p in pois if p.get("kind") == "Food"], key=dist)
    picked: list[dict] = []
    if foods:
        picked.append(foods[0])
    if stays:
        picked.append(stays[0])
    if len(foods) > 1:
        picked.append(foods[1])
    elif len(stays) > 1:
        picked.append(stays[1])
    # unique by id, max n
    seen: set[str] = set()
    out: list[dict] = []
    for p in picked:
        pid = str(p.get("id") or "")
        if pid in seen:
            continue
        seen.add(pid)
        out.append(p)
        if len(out) >= n:
            break
    return out


def parse_fm(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip().strip('"')
    return meta, parts[2].lstrip("\n")


def display_or_na(value: str, lang: str) -> str:
    v = (value or "").strip()
    if not v:
        return NA[lang]
    low = v.lower()
    if low in {
        "confirm with clinic",
        "ask the clinic",
        "클리닉에 문의",
        "클리닉へ확인",
    }:
        return NA[lang]
    return v


def build_body(
    lang: str,
    title: str,
    overview: str,
    address: str,
    tel: str,
    website: str,
    lat: float,
    lng: float,
    nearby: list[dict],
) -> str:
    lbl = LABELS[lang]
    na = NA[lang]
    ov = (overview or "").strip() or lbl["overview_empty"]
    tel_d = display_or_na(tel, lang)
    web_d = display_or_na(website, lang)
    addr_d = display_or_na(address, lang)
    home = "/" if lang == "en" else f"/?lang={lang}"

    before = {
        "en": """## Before you book

KR Care lists public KTO medical-tourism data. We do **not** verify prices, outcomes, or doctor credentials beyond the listing.

Ask the clinic directly about:

- Languages available for consultation
- Opening hours and holiday closures
- Deposit / cancellation rules
- What to bring (passport, medical history, translation)
""",
        "ja": """## Before you book

公開掲載情報以上の料金・効果・資格は保証しません。

次はクリニックへ直接ご確認ください:

- 相談可能な言語
- 診療時間・休診日
- 予約金・キャンセル規定
- 持参物（パスポート、診療歴、通訳）
""",
        "zh": """## Before you book

我们不保证超出公开信息的价格、疗效或资质。

请直接向诊所确认：

- 可用咨询语言
- 营业时间与休诊日
- 定金 / 取消规定
- 需携带物品（护照、病历、翻译）
""",
        "zh_tw": """## Before you book

我們不保證超出公開資訊的價格、療效或資格。

請直接向診所確認：

- 可用諮詢語言
- 營業時間與休診日
- 訂金 / 取消規定
- 需攜帶物品（護照、病歷、翻譯）
""",
    }[lang]

    checklist = {
        "en": """## Visit checklist

Bring / confirm before you go:

- [ ] Passport (and visa status if asked at reception)
- [ ] Appointment confirmation (name, time, procedure language)
- [ ] Payment method the clinic accepts (card / cash / transfer)
- [ ] Interpreter plan, if you need one
- [ ] Any medical history / medication list the clinic requested
- [ ] Light snack & water for aftercare (diet rules vary — ask staff)

KR Care does not book for you — double-check hours and deposits with the clinic.
""",
        "ja": """## Visit checklist

当日までに確認・持参：

- [ ] パスポート（受付で提示を求められる場合あり）
- [ ] 予約確認（氏名・時間・対応言語）
- [ ] 支払い方法（カード / 現金 / 振込）
- [ ] 通訳が必要な場合の手配
- [ ] クリニックから依頼された病歴・薬のリスト
- [ ] アフターケア用の軽い飲み物・軽食（食事制限はスタッフに確認）

KR Care は代理予約しません。診療時間・予約金はクリニックへ直接確認してください。
""",
        "zh": """## Visit checklist

出发前请确认 / 携带：

- [ ] 护照（前台可能要求出示）
- [ ] 预约确认（姓名、时间、可用语言）
- [ ] 诊所接受的支付方式（卡 / 现金 / 转账）
- [ ] 如需翻译，事先安排
- [ ] 诊所要求的病历 / 用药清单
- [ ] 护理后的清淡饮食与饮水（饮食限制请问工作人员）

KR Care 不代为预约。营业时间与定金请直接向诊所确认。
""",
        "zh_tw": """## Visit checklist

出發前請確認 / 攜帶：

- [ ] 護照（櫃檯可能要求出示）
- [ ] 預約確認（姓名、時間、可用語言）
- [ ] 診所接受的付款方式（卡 / 現金 / 轉帳）
- [ ] 如需翻譯，事先安排
- [ ] 診所要求的病歷 / 用藥清單
- [ ] 護理後的清淡飲食與飲水（飲食限制請問工作人員）

KR Care 不代為預約。營業時間與訂金請直接向診所確認。
""",
    }[lang]

    getting = {
        "en": f"""## Getting there

- **Address:** {addr_d}
- **Maps:** Use Open in Maps on this page for walking / transit directions (exit numbers change — confirm on Maps).
- **Buffer:** Add 15–20 minutes for building check-in and consultation.
- **Parking:** May be limited — ask the clinic when you book.
""",
        "ja": f"""## Getting there

- **住所:** {addr_d}
- **地図:** このページの「地図で見る」で徒歩・公共交通ルートを確認（出口番号は Maps で最新確認）。
- **余裕時間:** 受付・エレベーター・問診前の手続きで 15–20 分見ておきましょう。
- **駐車:** 限られることがあります。予約時にクリニックへ確認してください。
""",
        "zh": f"""## Getting there

- **地址:** {addr_d}
- **地图:** 请用本页「在地图中打开」查看步行/公交路线（出口编号请以地图为准）。
- **预留时间:** 大楼登记与挂号建议预留 15–20 分钟。
- **停车:** 可能紧张 — 预约时向诊所确认。
""",
        "zh_tw": f"""## Getting there

- **地址:** {addr_d}
- **地圖:** 請用本頁「在地圖中開啟」查看步行/大眾運輸路線（出口請以地圖為準）。
- **預留時間:** 大樓登記與掛號建議預留 15–20 分鐘。
- **停車:** 可能不足 — 預約時向診所確認。
""",
    }[lang]

    if nearby:
        intro = {
            "en": f"KR Care Pick pins near this clinic (map curation — confirm hours yourself). Open in Google Maps, or browse Stay / Food on the [KR Care map]({home}).",
            "ja": f"このクリニック周辺の KR Care Pick（地図キュレーション）。Google Maps で開くか、[KR Care 地図]({home}) で Stay / Food を表示。営業時間は各自確認を。",
            "zh": f"本诊所附近的 KR Care Pick（地图策展）。可在 Google Maps 打开，或到 [KR Care 地图]({home}) 查看 Stay / Food。请自行确认营业时间。",
            "zh_tw": f"本診所附近的 KR Care Pick（地圖策展）。可在 Google Maps 開啟，或到 [KR Care 地圖]({home}) 查看 Stay / Food。請自行確認營業時間。",
        }[lang]
        kind_lbl = {"Stay": {"en": "Stay", "ja": "Stay", "zh": "住宿", "zh_tw": "住宿"}, "Food": {"en": "Food", "ja": "Food", "zh": "餐饮", "zh_tw": "餐飲"}}
        walk = {"en": "m walk", "ja": "m", "zh": "m", "zh_tw": "m"}[lang]
        lines = [f"## Nearby stay & food\n\n{intro}\n"]
        for p in nearby:
            loc = (p.get("i18n") or {}).get(lang) or (p.get("i18n") or {}).get("en") or {}
            title_p = loc.get("title") or p.get("id") or "Place"
            short = re.sub(r"\s*\([^)]*\)\s*$", "", title_p).strip() or title_p
            meters = int(round(haversine_m(lat, lng, float(p["lat"]), float(p["lng"]))))
            url = f"https://www.google.com/maps?q={p['lat']},{p['lng']}"
            tip = (loc.get("transit") or "").strip()
            kind = p.get("kind") or "Place"
            kl = kind_lbl.get(kind, {}).get(lang, kind)
            tip_s = f" — {tip}" if tip else ""
            lines.append(f"- **{kl} · ~{meters}{walk}:** [{short}]({url}){tip_s}\n")
        nearby_md = "".join(lines)
    else:
        nearby_md = {
            "en": f"""## Nearby stay & food

Not in public listing for curated Stay/Food pins near this clinic — browse Stay / Food on the [KR Care map]({home}), or ask the clinic for local tips.
""",
            "ja": f"""## Nearby stay & food

このクリニック向けの Stay/Food キュレーションは公開データにありません。[KR Care 地図]({home}) で Stay / Food を見るか、クリニックへお尋ねください。
""",
            "zh": f"""## Nearby stay & food

公开数据中暂无该诊所附近的 Stay/Food 策展点 — 请到 [KR Care 地图]({home}) 查看，或向诊所咨询。
""",
            "zh_tw": f"""## Nearby stay & food

公開資料中暫無此診所附近的 Stay/Food 策展點 — 請到 [KR Care 地圖]({home}) 查看，或向診所詢問。
""",
        }[lang]

    listed = f"""## Listed details

- **{lbl['phone']}:** {tel_d}
- **{lbl['address']}:** {addr_d}
- **{lbl['website']}:** {web_d}
- **{lbl['source']}:** {SOURCE[lang]}
"""

    return (
        f"## Overview\n\n{ov}\n\n"
        f"{listed}\n"
        f"{before}\n"
        f"{checklist}\n"
        f"{getting}\n"
        f"{nearby_md}".rstrip()
        + "\n"
    )


def enrich_one(
    path: Path,
    nearby_idx: dict[str, list[dict]],
    detail_cache: dict[tuple[str, str], dict],
    skip_api: bool,
) -> bool:
    text = path.read_text(encoding="utf-8")
    meta, _body = parse_fm(text)
    lang = meta.get("lang") or "en"
    if lang not in LANGS:
        lang = "en"
    base = path.name.replace(f"_{lang}.md", "")
    cid = (meta.get("content_id") or "").strip() or base.replace("mdcl_", "")
    title = meta.get("title") or base
    try:
        lat = float(meta.get("lat") or 0)
        lng = float(meta.get("lng") or 0)
    except ValueError:
        lat = lng = 0.0

    tel = meta.get("tel") or ""
    website = meta.get("website") or ""
    address = meta.get("address") or ""
    overview = ""

    if not skip_api and cid:
        cache_key = (LANG_DIV[lang], cid)
        if cache_key not in detail_cache:
            try:
                detail_cache[cache_key] = first_item(
                    fetch_json(
                        {
                            "MobileOS": "ETC",
                            "MobileApp": "KRCare",
                            "_type": "json",
                            "langDivCd": LANG_DIV[lang],
                            "contentId": cid,
                        }
                    )
                )
            except Exception as exc:
                print(f"  detail fail {path.name}: {exc}")
                detail_cache[cache_key] = {}
        d = detail_cache.get(cache_key) or {}
        if d:
            overview = clean_html(d.get("overview") or "")
            address = address_of(d) or address
            tel = (d.get("tel") or "").strip() or tel
            website = (d.get("homepage") or d.get("homePage") or "").strip() or website
            if d.get("title"):
                title = str(d.get("title")).strip()
            try:
                if d.get("mapY"):
                    lat = float(d["mapY"])
                if d.get("mapX"):
                    lng = float(d["mapX"])
            except (TypeError, ValueError):
                pass

    nearby = pick_nearby(nearby_idx.get(base, []), lat, lng, 3)
    body = build_body(lang, title, overview, address, tel, website, lat, lng, nearby)
    summary = re.sub(r"\s+", " ", overview or LABELS[lang]["overview_empty"])[:280]
    if len(re.sub(r"\s+", " ", overview or "")) > 280:
        summary += "…"

    thumb = meta.get("thumbnail") or f"/static/images/{base}.jpg"
    today = date.today().isoformat()
    md = f"""---
lang: {lang}
title: "{esc(title)}"
lat: {lat}
lng: {lng}
categories: ["Clinic"]
thumbnail: "{esc(thumb)}"
address: "{esc(address)}"
date: "{today}"
website: "{esc(website)}"
tel: "{esc(tel)}"
source_image: "{esc(meta.get('source_image') or '')}"
summary: "{esc(summary)}"
image_prompt: ""
content_id: "{esc(cid)}"
source: "MdclTursmService"
---

{body}
"""
    path.write_text(md, encoding="utf-8")
    return True


def needs_tourapi(path: Path) -> bool:
    """True when overview still looks empty / placeholder (TourAPI not applied yet)."""
    text = path.read_text(encoding="utf-8")
    m = re.search(r"## Overview\n\n(.+?)(?:\n## |\Z)", text, re.S)
    ov = (m.group(1).strip() if m else "")
    if len(ov) >= 120:
        markers = (
            "No public overview",
            "公開の紹介文がありません",
            "公开数据中暂无介绍",
            "公開資料中暫無介紹",
            "listed in Korea Tourism Organization medical-tourism OpenAPI",
            "韓国観光公社の医療ツーリズムOpenAPI掲載情報です",
            "韩国旅游发展局医疗观光 OpenAPI 收录信息",
            "韓國觀光公社醫療觀光 OpenAPI 收錄資訊",
        )
        if any(x in ov for x in markers):
            return True
        return False
    return True


def prefetch_details(files: list[Path], workers: int = 3) -> dict[tuple[str, str], dict]:
    """Fetch unique TourAPI details with limited concurrency + 429 retries."""
    jobs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for path in files:
        meta, _ = parse_fm(path.read_text(encoding="utf-8"))
        lang = meta.get("lang") or "en"
        if lang not in LANGS:
            lang = "en"
        cid = (meta.get("content_id") or "").strip()
        if not cid:
            base = path.name
            for suf in LANGS:
                if base.endswith(f"_{suf}.md"):
                    cid = base[: -(len(suf) + 4)].replace("mdcl_", "")
                    break
        key = (LANG_DIV[lang], cid)
        if cid and key not in seen:
            seen.add(key)
            jobs.append(key)

    cache: dict[tuple[str, str], dict] = {}
    total = len(jobs)
    workers = max(1, min(workers, 4))
    print(f"TourAPI detail prefetch: {total} unique requests, workers={workers}", flush=True)
    if not jobs:
        return cache

    def _one(key: tuple[str, str]) -> tuple[tuple[str, str], dict]:
        lang_div, cid = key
        time.sleep(1.0 if workers == 1 else 0.35)
        try:
            item = first_item(
                fetch_json(
                    {
                        "MobileOS": "ETC",
                        "MobileApp": "KRCare",
                        "_type": "json",
                        "langDivCd": lang_div,
                        "contentId": cid,
                    }
                )
            )
            return key, item
        except Exception as exc:
            print(f"  detail fail {lang_div}/{cid}: {exc}", flush=True)
            return key, {}

    done = 0
    ok = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_one, j) for j in jobs]
        for fut in concurrent.futures.as_completed(futs):
            key, item = fut.result()
            cache[key] = item
            done += 1
            if item:
                ok += 1
            if done % 40 == 0 or done == total:
                print(
                    f"  api progress {done}/{total} ({100 * done / total:.0f}%) ok={ok}",
                    flush=True,
                )
    return cache


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--skip-api", action="store_true")
    ap.add_argument(
        "--only-missing",
        action="store_true",
        help="Only files that lack ## Visit checklist",
    )
    ap.add_argument(
        "--needs-api",
        action="store_true",
        help="Only files whose Overview still looks like a placeholder",
    )
    ap.add_argument("--workers", type=int, default=1, help="Parallel TourAPI fetches (use 1 if rate-limited)")
    ap.add_argument(
        "--en-only",
        action="store_true",
        help="Only fetch ENG TourAPI details; apply tel/website/overview to all langs of that clinic",
    )
    args = ap.parse_args()

    files = sorted(CONTENT_DIR.glob("mdcl_*.md"))
    if args.only_missing:
        files = [p for p in files if "## Visit checklist" not in p.read_text(encoding="utf-8")]
    if args.needs_api:
        files = [p for p in files if needs_tourapi(p)]
    if args.en_only:
        # Fetch ENG details only, then rewrite all language files for those clinics.
        bases: set[str] = set()
        for p in files:
            if p.name.endswith("_en.md"):
                bases.add(p.name[: -len("_en.md")])
        files = sorted(
            CONTENT_DIR / f"{b}_{lang}.md"
            for b in bases
            for lang in LANGS
            if (CONTENT_DIR / f"{b}_{lang}.md").exists()
        )
        fetch_files = [CONTENT_DIR / f"{b}_en.md" for b in sorted(bases) if (CONTENT_DIR / f"{b}_en.md").exists()]
    else:
        fetch_files = files

    if args.limit:
        bases_lim: list[str] = []
        seen: set[str] = set()
        for p in files:
            for lang in LANGS:
                suf = f"_{lang}.md"
                if p.name.endswith(suf):
                    b = p.name[: -len(suf)]
                    if b not in seen:
                        seen.add(b)
                        bases_lim.append(b)
                    break
            if len(bases_lim) >= args.limit:
                break
        allow = set(bases_lim)
        files = [p for p in files if any(p.name.startswith(f"{b}_") and p.name[len(b)] == "_" for b in allow)]
        fetch_files = [p for p in fetch_files if any(p.name.startswith(f"{b}_") for b in allow)]

    nearby_idx = load_nearby_index()
    print(f"Enriching {len(files)} files (skip_api={args.skip_api}, en_only={args.en_only})…", flush=True)

    detail_cache: dict[tuple[str, str], dict] = {}
    if not args.skip_api and fetch_files:
        detail_cache = prefetch_details(fetch_files, workers=max(1, args.workers))
        if args.en_only:
            # Reuse ENG payload for other langs (tel/website/overview); titles stay per-file meta unless API title used for EN only.
            for path in files:
                if path.name.endswith("_en.md"):
                    continue
                meta, _ = parse_fm(path.read_text(encoding="utf-8"))
                lang = meta.get("lang") or "en"
                # map to ENG sibling content id from en file
                base = path.name.rsplit("_", 1)[0]
                # fix: zh_tw
                for suf in ("zh_tw", "en", "ja", "zh"):
                    if path.name.endswith(f"_{suf}.md"):
                        base = path.name[: -(len(suf) + 4)]
                        break
                en_meta, _ = parse_fm((CONTENT_DIR / f"{base}_en.md").read_text(encoding="utf-8"))
                en_cid = (en_meta.get("content_id") or "").strip()
                eng = detail_cache.get(("ENG", en_cid)) or {}
                cid = (meta.get("content_id") or "").strip()
                if eng and cid:
                    detail_cache.setdefault((LANG_DIV.get(lang, "ENG"), cid), eng)

    done = 0
    total = len(files)
    for i, path in enumerate(files, 1):
        enrich_one(path, nearby_idx, detail_cache, args.skip_api)
        done += 1
        if i % 40 == 0 or i == total:
            print(f"  write progress {i}/{total} ({100 * i / total:.0f}%)", flush=True)
    print(f"done: {done} files", flush=True)

if __name__ == "__main__":
    main()
