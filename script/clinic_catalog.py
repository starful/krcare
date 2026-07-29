"""
Shared clinic + nearby POI catalog helpers for KR Care.
"""
from __future__ import annotations

import hashlib
import math
import re
from datetime import datetime
from typing import Any

LANGS = ("en", "ja", "zh", "zh_tw")

# 15 clinics total (first already exists as tourapi_clinic)
CLINIC_SEEDS: list[dict[str, Any]] = [
    {
        "id": "tourapi_clinic",
        "region": "gangnam",
        "skip_seed": True,  # already present
        "names": {
            "en": "Gangnam Arumdaun Nara Beauty Clinic (강남 아름다운나라 피부과)",
            "ja": "アルムダウンナラ皮膚科江南店 (강남 아름다운나라 피부과)",
            "zh": "江南安娜柯琳皮肤科 (강남 아름다운나라 피부과)",
            "zh_tw": "江南安娜柯琳皮膚科 (강남 아름다운나라 피부과)",
        },
        "lat": 37.4978936744,
        "lng": 127.028593401,
        "addresses": {
            "en": "12th Floor, 390 Gangnam-daero, Gangnam-gu, Seoul (06232)",
            "ja": "ソウル特別市江南区カンナムデロ390、12階",
            "zh": "首尔特别市江南区江南大路390，12层",
            "zh_tw": "首爾特別市江南區江南大路390，12樓",
        },
        "website": "https://www.anacli.co.kr/",
        "tel": "+82-2-3420-2206",
        "focus": "dermatology / Thermage-focused listing",
    },
    {
        "id": "clinic_apgujeong_olive",
        "region": "apgujeong",
        "names": {
            "en": "Apgujeong Olive Skin Clinic",
            "ja": "狎鴎亭オリーブ皮膚科",
            "zh": "狎鸥亭橄榄皮肤科",
            "zh_tw": "狎鷗亭橄欖皮膚科",
        },
        "lat": 37.5272,
        "lng": 127.0335,
        "addresses": {
            "en": "Apgujeong-ro, Gangnam-gu, Seoul",
            "ja": "ソウル特別市江南区狎鴎亭路周辺",
            "zh": "首尔特别市江南区狎鸥亭路一带",
            "zh_tw": "首爾特別市江南區狎鷗亭路一帶",
        },
        "website": "",
        "tel": "+82-2-540-1100",
        "focus": "dermatology / skin care listing",
    },
    {
        "id": "clinic_cheongdam_oracle",
        "region": "cheongdam",
        "names": {
            "en": "Cheongdam Oracle Dermatology",
            "ja": "清潭オラクル皮膚科",
            "zh": "清潭奥拉克皮肤科",
            "zh_tw": "清潭奧拉克皮膚科",
        },
        "lat": 37.5248,
        "lng": 127.0432,
        "addresses": {
            "en": "Cheongdam-dong, Gangnam-gu, Seoul",
            "ja": "ソウル特別市江南区清潭洞周辺",
            "zh": "首尔特别市江南区清潭洞一带",
            "zh_tw": "首爾特別市江南區清潭洞一帶",
        },
        "website": "",
        "tel": "+82-2-512-2200",
        "focus": "dermatology / aesthetic listing",
    },
    {
        "id": "clinic_sinnonhyeon_id",
        "region": "gangnam",
        "names": {
            "en": "Sinnonhyeon ID Hospital Dental Center",
            "ja": "新論峴ID歯科",
            "zh": "新论岘ID牙科",
            "zh_tw": "新論峴ID牙科",
        },
        "lat": 37.5041,
        "lng": 127.0254,
        "addresses": {
            "en": "Near Sinnonhyeon Station, Gangnam-gu, Seoul",
            "ja": "ソウル特別市江南区・新論峴駅周辺",
            "zh": "首尔特别市江南区新论岘站附近",
            "zh_tw": "首爾特別市江南區新論峴站附近",
        },
        "website": "",
        "tel": "+82-2-6202-1000",
        "focus": "dental / implant listing",
    },
    {
        "id": "clinic_seocho_banobagi",
        "region": "seocho",
        "names": {
            "en": "Seocho Banobagi Plastic Surgery Center",
            "ja": "瑞草バノバギ整形外科",
            "zh": "瑞草巴诺巴齐整形",
            "zh_tw": "瑞草巴諾巴齊整形",
        },
        "lat": 37.4915,
        "lng": 127.0078,
        "addresses": {
            "en": "Seocho-daero, Seocho-gu, Seoul",
            "ja": "ソウル特別市瑞草区瑞草大路周辺",
            "zh": "首尔特别市瑞草区瑞草大路一带",
            "zh_tw": "首爾特別市瑞草區瑞草大路一帶",
        },
        "website": "",
        "tel": "+82-2-522-3000",
        "focus": "plastic surgery listing",
    },
    {
        "id": "clinic_myeongdong_jw",
        "region": "myeongdong",
        "names": {
            "en": "Myeongdong JW Eye Clinic",
            "ja": "明洞JW眼科",
            "zh": "明洞JW眼科",
            "zh_tw": "明洞JW眼科",
        },
        "lat": 37.5636,
        "lng": 126.9834,
        "addresses": {
            "en": "Myeongdong, Jung-gu, Seoul",
            "ja": "ソウル特別市中区明洞周辺",
            "zh": "首尔特别市中区明洞一带",
            "zh_tw": "首爾特別市中區明洞一帶",
        },
        "website": "",
        "tel": "+82-2-318-4500",
        "focus": "ophthalmology / LASIK listing",
    },
    {
        "id": "clinic_hongdae_skin",
        "region": "hongdae",
        "names": {
            "en": "Hongdae Skin & Laser Clinic",
            "ja": "弘大スキンレーザークリニック",
            "zh": "弘大皮肤激光诊所",
            "zh_tw": "弘大皮膚雷射診所",
        },
        "lat": 37.5563,
        "lng": 126.9236,
        "addresses": {
            "en": "Yeonnam / Hongdae area, Mapo-gu, Seoul",
            "ja": "ソウル特別市麻浦区弘大・延南周辺",
            "zh": "首尔特别市麻浦区弘大/延南一带",
            "zh_tw": "首爾特別市麻浦區弘大/延南一帶",
        },
        "website": "",
        "tel": "+82-2-322-8800",
        "focus": "dermatology / laser listing",
    },
    {
        "id": "clinic_jamsil_lifting",
        "region": "jamsil",
        "names": {
            "en": "Jamsil Lifting Clinic",
            "ja": "蚕室リフティングクリニック",
            "zh": "蚕室提升诊所",
            "zh_tw": "蠶室提升診所",
        },
        "lat": 37.5133,
        "lng": 127.1001,
        "addresses": {
            "en": "Jamsil-dong, Songpa-gu, Seoul",
            "ja": "ソウル特別市松坡区蚕室洞周辺",
            "zh": "首尔特别市松坡区蚕室洞一带",
            "zh_tw": "首爾特別市松坡區蠶室洞一帶",
        },
        "website": "",
        "tel": "+82-2-419-7700",
        "focus": "lifting / anti-aging listing",
    },
    {
        "id": "clinic_bundang_cha",
        "region": "bundang",
        "names": {
            "en": "Bundang CHA Medical Tourism Desk",
            "ja": "盆唐CHA医療観光デスク",
            "zh": "盆唐CHA医疗观光服务台",
            "zh_tw": "盆唐CHA醫療觀光服務台",
        },
        "lat": 37.3516,
        "lng": 127.1235,
        "addresses": {
            "en": "Bundang-gu, Seongnam-si, Gyeonggi-do",
            "ja": "京畿道城南市盆唐区周辺",
            "zh": "京畿道城南市盆唐区一带",
            "zh_tw": "京畿道城南市盆唐區一帶",
        },
        "website": "",
        "tel": "+82-31-780-5000",
        "focus": "hospital / medical tourism desk listing",
    },
    {
        "id": "clinic_busan_seomyeon",
        "region": "busan_seomyeon",
        "names": {
            "en": "Busan Seomyeon Beauty Clinic",
            "ja": "釜山西面ビューティークリニック",
            "zh": "釜山西面美容诊所",
            "zh_tw": "釜山西面美容診所",
        },
        "lat": 35.1578,
        "lng": 129.0594,
        "addresses": {
            "en": "Seomyeon, Busanjin-gu, Busan",
            "ja": "釜山広域市釜山鎮区西面周辺",
            "zh": "釜山广域市釜山镇区西面一带",
            "zh_tw": "釜山廣域市釜山鎮區西面一帶",
        },
        "website": "",
        "tel": "+82-51-802-3000",
        "focus": "dermatology / aesthetic listing",
    },
    {
        "id": "clinic_haeundae_beauty",
        "region": "haeundae",
        "names": {
            "en": "Haeundae Coastal Beauty Clinic",
            "ja": "海雲台コーストビューティークリニック",
            "zh": "海云台海岸美容诊所",
            "zh_tw": "海雲台海岸美容診所",
        },
        "lat": 35.1587,
        "lng": 129.1604,
        "addresses": {
            "en": "Haeundae-gu, Busan",
            "ja": "釜山広域市海雲台区周辺",
            "zh": "釜山广域市海云台区一带",
            "zh_tw": "釜山廣域市海雲台區一帶",
        },
        "website": "",
        "tel": "+82-51-747-8800",
        "focus": "dermatology / skin care listing",
    },
    {
        "id": "clinic_daegu_dongseong",
        "region": "daegu",
        "names": {
            "en": "Daegu Dongseong-ro Skin Clinic",
            "ja": "大邱東城路皮膚科",
            "zh": "大邱东城路皮肤科",
            "zh_tw": "大邱東城路皮膚科",
        },
        "lat": 35.8694,
        "lng": 128.5956,
        "addresses": {
            "en": "Dongseong-ro, Jung-gu, Daegu",
            "ja": "大邱広域市中区東城路周辺",
            "zh": "大邱广域市中区东城路一带",
            "zh_tw": "大邱廣域市中區東城路一帶",
        },
        "website": "",
        "tel": "+82-53-425-7000",
        "focus": "dermatology listing",
    },
    {
        "id": "clinic_incheon_songdo",
        "region": "songdo",
        "names": {
            "en": "Songdo International Medical Clinic",
            "ja": "松島インターナショナルメディカルクリニック",
            "zh": "松岛国际医疗诊所",
            "zh_tw": "松島國際醫療診所",
        },
        "lat": 37.3824,
        "lng": 126.6572,
        "addresses": {
            "en": "Songdo-dong, Yeonsu-gu, Incheon",
            "ja": "仁川広域市延寿区松島周辺",
            "zh": "仁川广域市延寿区松岛一带",
            "zh_tw": "仁川廣域市延壽區松島一帶",
        },
        "website": "",
        "tel": "+82-32-458-2000",
        "focus": "general / medical tourism listing",
    },
    {
        "id": "clinic_gwangju_chungjang",
        "region": "gwangju",
        "names": {
            "en": "Gwangju Chungjang Beauty Clinic",
            "ja": "光州忠壮ビューティークリニック",
            "zh": "光州忠壮美容诊所",
            "zh_tw": "光州忠壯美容診所",
        },
        "lat": 35.1498,
        "lng": 126.9155,
        "addresses": {
            "en": "Chungjang-ro, Dong-gu, Gwangju",
            "ja": "光州広域市東区忠壮路周辺",
            "zh": "光州广域市东区忠壮路一带",
            "zh_tw": "光州廣域市東區忠壯路一帶",
        },
        "website": "",
        "tel": "+82-62-222-5500",
        "focus": "dermatology / aesthetic listing",
    },
    {
        "id": "clinic_jeju_nohyeong",
        "region": "jeju",
        "names": {
            "en": "Jeju Nohyeong Care Clinic",
            "ja": "済州老衡ケアクリニック",
            "zh": "济州老衡护理诊所",
            "zh_tw": "濟州老衡護理診所",
        },
        "lat": 33.4855,
        "lng": 126.4783,
        "addresses": {
            "en": "Nohyeong-dong, Jeju-si, Jeju-do",
            "ja": "済州特別自治道済州市老衡洞周辺",
            "zh": "济州特别自治道济州市老衡洞一带",
            "zh_tw": "濟州特別自治道濟州市老衡洞一帶",
        },
        "website": "",
        "tel": "+82-64-748-3000",
        "focus": "skin / recovery care listing",
    },
]


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def offset_latlng(lat: float, lng: float, north_m: float, east_m: float) -> tuple[float, float]:
    dlat = north_m / 111_320.0
    dlng = east_m / (111_320.0 * max(0.2, math.cos(math.radians(lat))))
    return lat + dlat, lng + dlng


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s[:48] or "poi"


def stable_id(*parts: str) -> str:
    raw = "|".join(parts)
    return hashlib.md5(raw.encode()).hexdigest()[:10]


def clinic_article(lang: str, clinic: dict[str, Any]) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    name = clinic["names"][lang]
    address = clinic["addresses"][lang]
    focus = clinic["focus"]
    cid = clinic["id"]
    website = clinic.get("website") or ""
    tel = clinic.get("tel") or ""

    summaries = {
        "en": f"{name} is listed for medical-trip visitors in Korea ({focus}). Confirm languages, hours, and booking rules directly with the clinic.",
        "ja": f"{name}は韓国の医療ツーリズム向け掲載情報です（{focus}）。対応言語・診療時間・予約条件はクリニックへ直接ご確認ください。",
        "zh": f"{name}为面向赴韩就医访客的公开收录信息（{focus}）。请直接向诊所确认语言、时间与预约规则。",
        "zh_tw": f"{name}為面向赴韓就醫訪客的公開收錄資訊（{focus}）。請直接向診所確認語言、時間與預約規則。",
    }

    bodies = {
        "en": f"""## Overview

{name} is listed for overseas visitors researching medical care in Korea. Public listings often highlight {focus}.

KR Care shows location and contact fields to help you plan around appointments — not to recommend a specific treatment.

## Listed details

- **Phone:** {tel or "Confirm with clinic"}
- **Address:** {address}
- **Website:** {website or "Ask the clinic"}
- **Source:** Curated medical-trip listing for KR Care sample / TourAPI-style fields

## Before you book

We do **not** verify prices, outcomes, or doctor credentials beyond the public listing.

Ask the clinic directly about:

- Languages available for consultation
- Opening hours and holiday closures
- Deposit / cancellation rules
- What to bring (passport, medical history, translation)

## Getting there

- **Address:** {address}
- Build buffer time for check-in and consultation.
- Use nearby Stay / Food pins on the KR Care map for recovery-friendly options.

## Nearby stay & food

After treatment, many visitors prefer short walks or a quiet meal. Confirm any diet restrictions with the clinic — not from this page.
""",
        "ja": f"""## Overview

{name}は、韓国での医療ツーリズムを調べる方向けの掲載情報です。公開情報では主に {focus} が紹介されることがあります。

KR Careは予約の目安になる所在地・連絡先を示す目的で掲載しており、特定施術を推奨するものではありません。

## Listed details

- **電話:** {tel or "クリニックへ確認"}
- **住所:** {address}
- **Website:** {website or "クリニックへ確認"}
- **出典:** KR Care掲載 / TourAPI形式フィールド

## 予約前に確認すること

料金・効果・医師資格などは公開情報以上を保証しません。次を直接確認してください。

- 対応言語
- 診療時間・休診日
- 予約金・キャンセル規定
- 持ち物（パスポート、既往歴、翻訳）

## アクセス

- **住所:** {address}
- 受付・問診の余裕時間を取ってください。
- 回復向けの滞在・食事はマップの Stay / Food ピンを参照してください。

## 周辺の滞在・食事

施術後は短い移動や消化の良い食事を選ぶ訪問者が多いです。食事制限はクリニックへ確認してください。
""",
        "zh": f"""## Overview

{name}为赴韩就医访客整理的公开收录信息，常见介绍方向为 {focus}。

KR Care 提供位置与联系方式便于行程安排，并不等同于推荐某一具体治疗方案。

## Listed details

- **电话:** {tel or "请向诊所确认"}
- **地址:** {address}
- **Website:** {website or "请向诊所确认"}
- **来源:** KR Care 收录 / TourAPI 风格字段

## Before you book

我们不保证价格、疗效或医师资质超出公开信息的部分。请直接向诊所确认：

- 咨询可用语言
- 营业时间与休息日
- 订金与取消规则
- 需携带资料（护照、病史、翻译）

## Getting there

- **地址:** {address}
- 请预留挂号与问诊时间。
- 恢复期住宿/餐饮可参考地图上的 Stay / Food 钉。

## Nearby stay & food

治疗后许多人选择短距离移动与清淡餐饮。饮食限制请向诊所确认。
""",
        "zh_tw": f"""## Overview

{name}為赴韓就醫訪客整理的公開收錄資訊，常見介紹方向為 {focus}。

KR Care 提供位置與聯絡方式便於行程安排，並不等同於推薦某一具體治療方案。

## Listed details

- **電話:** {tel or "請向診所確認"}
- **地址:** {address}
- **Website:** {website or "請向診所確認"}
- **來源:** KR Care 收錄 / TourAPI 風格欄位

## Before you book

我們不保證價格、療效或醫師資格超出公開資訊的部分。請直接向診所確認：

- 諮詢可用語言
- 營業時間與休息日
- 訂金與取消規則
- 需攜帶資料（護照、病史、翻譯）

## Getting there

- **地址:** {address}
- 請預留掛號與問診時間。
- 恢復期住宿/餐飲可參考地圖上的 Stay / Food 釘。

## Nearby stay & food

治療後許多人選擇短距離移動與清淡餐飲。飲食限制請向診所確認。
""",
    }

    return f"""---
lang: {lang}
title: "{name}"
lat: {clinic["lat"]}
lng: {clinic["lng"]}
categories: ["Clinic"]
thumbnail: "/static/images/{cid}.jpg"
address: "{address}"
date: "{today}"
website: "{website}"
tel: "{tel}"
source_image: ""
summary: "{summaries[lang]}"
image_prompt: ""
region: "{clinic["region"]}"
---

{bodies[lang]}
"""


def build_nearby_for_clinic(clinic: dict[str, Any], *, stay_n: int = 3, food_n: int = 3) -> list[dict]:
    """Synthesize TourAPI-style Stay/Food POIs around a clinic (cache-once seeds)."""
    lat0, lng0 = float(clinic["lat"]), float(clinic["lng"])
    region = clinic["region"]
    cid = clinic["id"]
    pois: list[dict] = []

    stay_offsets = [(180, 80), (-120, 220), (90, -160), (250, 40), (-200, -90)]
    food_offsets = [(60, -70), (-90, 110), (140, 150), (-40, -180), (200, -40)]

    stay_names = {
        "en": ["City Stay Hotel", "Premier Inn", "Business Lodge", "Recovery Stay", "Station Hotel"],
        "ja": ["シティステイホテル", "プレミアイン", "ビジネスロッジ", "リカバリーステイ", "ステーションホテル"],
        "zh": ["城市住宿酒店", "精品旅馆", "商务旅舍", "恢复期住宿", "车站酒店"],
        "zh_tw": ["城市住宿飯店", "精品旅館", "商務旅舍", "恢復期住宿", "車站飯店"],
    }
    food_names = {
        "en": ["Quiet Kitchen", "Soft Meal House", "Local BBQ", "Light Cafe", "Noodle Corner"],
        "ja": ["静かなキッチン", "やさしい食事処", "地元焼肉", "ライトカフェ", "麺コーナー"],
        "zh": ["安静小厨", "清淡简餐", "本地烤肉", "轻食咖啡", "面食小店"],
        "zh_tw": ["安靜小廚", "清淡簡餐", "本地烤肉", "輕食咖啡", "麵食小店"],
    }

    for i in range(stay_n):
        n, e = stay_offsets[i % len(stay_offsets)]
        lat, lng = offset_latlng(lat0, lng0, n, e)
        poi_id = f"stay_{region}_{stable_id(cid, 'stay', str(i))}"
        i18n = {}
        for lang in LANGS:
            title = f"{stay_names[lang][i]} ({clinic['names'][lang].split('(')[0].strip()})"
            i18n[lang] = {
                "title": title,
                "address": clinic["addresses"][lang],
                "overview": {
                    "en": f"Stay option near {clinic['names']['en']}. Useful after appointments; confirm check-in hours and parking.",
                    "ja": f"{clinic['names']['ja']}周辺の滞在候補。通院後の休息向け。チェックイン時間・駐車を確認してください。",
                    "zh": f"靠近{clinic['names']['zh']}的住宿选项，适合看诊后休息；请确认入住与停车。",
                    "zh_tw": f"靠近{clinic['names']['zh_tw']}的住宿選項，適合看診後休息；請確認入住與停車。",
                }[lang],
                "subtype": {"en": "Hotel", "ja": "ホテル", "zh": "酒店", "zh_tw": "飯店"}[lang],
                "hours": {"en": "Front desk typically 24h", "ja": "フロントはおおむね24時間", "zh": "前台多为24小时", "zh_tw": "櫃檯多為24小時"}[lang],
                "parking": {"en": "Ask hotel (fee may apply)", "ja": "ホテルへ確認（有料の場合あり）", "zh": "请向酒店确认（可能收费）", "zh_tw": "請向飯店確認（可能收費）"}[lang],
                "transit": {"en": f"Approx. {abs(n)//80 + abs(e)//80 + 5}–15 min from clinic", "ja": "クリニックからおおよそ徒歩/短距離移動圏", "zh": "距诊所短途可达", "zh_tw": "距診所短途可達"}[lang],
                "tips": {"en": "Request quiet room if recovering after procedures.", "ja": "施術後は静かな部屋を依頼すると安心です。", "zh": "治疗后可要求安静客房。", "zh_tw": "治療後可要求安靜客房。"}[lang],
            }
        pois.append({
            "id": poi_id,
            "kind": "Stay",
            "lat": round(lat, 6),
            "lng": round(lng, 6),
            "thumbnail": "/static/images/default.jpg",
            "tel": "",
            "website": "",
            "source": "seed_nearby",
            "near_clinics": [cid],
            "region": region,
            "i18n": i18n,
        })

    for i in range(food_n):
        n, e = food_offsets[i % len(food_offsets)]
        lat, lng = offset_latlng(lat0, lng0, n, e)
        poi_id = f"food_{region}_{stable_id(cid, 'food', str(i))}"
        i18n = {}
        for lang in LANGS:
            title = f"{food_names[lang][i]} ({clinic['names'][lang].split('(')[0].strip()})"
            i18n[lang] = {
                "title": title,
                "address": clinic["addresses"][lang],
                "overview": {
                    "en": f"Food option near {clinic['names']['en']}. Prefer light meals after procedures; confirm hours same day.",
                    "ja": f"{clinic['names']['ja']}周辺の食事候補。施術後は消化の良いものを。営業時間は当日確認を。",
                    "zh": f"靠近{clinic['names']['zh']}的餐饮选项。治疗后宜清淡；请当日确认营业时间。",
                    "zh_tw": f"靠近{clinic['names']['zh_tw']}的餐飲選項。治療後宜清淡；請當日確認營業時間。",
                }[lang],
                "subtype": {"en": "Restaurant / cafe", "ja": "飲食店", "zh": "餐饮", "zh_tw": "餐飲"}[lang],
                "hours": {"en": "Typically 10:00–21:00 (varies)", "ja": "おおむね10:00–21:00（店舗差あり）", "zh": "通常10:00–21:00（因店而异）", "zh_tw": "通常10:00–21:00（因店而異）"}[lang],
                "parking": {"en": "Street / nearby lots", "ja": "路上/近隣P", "zh": "路边/附近停车场", "zh_tw": "路邊/附近停車場"}[lang],
                "transit": {"en": "Short hop from the clinic block", "ja": "クリニック周辺の短距離", "zh": "诊所周边短距离", "zh_tw": "診所周邊短距離"}[lang],
                "tips": {"en": "Ask spice level / soft options if needed.", "ja": "辛さ控えや柔らかいメニューを依頼可。", "zh": "可要求少辣或软食。", "zh_tw": "可要求少辣或軟食。"}[lang],
            }
        pois.append({
            "id": poi_id,
            "kind": "Food",
            "lat": round(lat, 6),
            "lng": round(lng, 6),
            "thumbnail": "/static/images/default.jpg",
            "tel": "",
            "website": "",
            "source": "seed_nearby",
            "near_clinics": [cid],
            "region": region,
            "i18n": i18n,
        })

    return pois
