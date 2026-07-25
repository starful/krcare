"""
KR Care item content generator.
- Reads script/csv/items.csv and writes app/content/{safe}_{lang}.md
- Images are NOT generated here: fetch_images.py handles
  TourAPI source_image → Places → default.jpg (once), then GCS upload via deploy.sh
"""
import os
import csv
import re
import concurrent.futures
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def _claude_md(prompt: str) -> str:
    """MD text via Claude CLI subscription (not Claude API)."""
    import sys
    from pathlib import Path
    _shared = Path(__file__).resolve().parents[2] / "shared"
    if str(_shared) not in sys.path:
        sys.path.insert(0, str(_shared))
    from site_llm import generate_md_text
    return generate_md_text(prompt)

# GEMINI_API_KEY no longer required for MD (Claude CLI)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CONTENT_DIR = os.path.join(BASE_DIR, "app", "content")

PROMPT_CONFIG = {
    "item_type": "medical clinic / care facility in Korea",
    "item_type_ko": "한국 의료·케어 시설",
    "categories": {
        "en": ["Clinic", "Stay", "Food"],
        "ja": ["Clinic", "Stay", "Food"],
        "zh": ["Clinic", "Stay", "Food"],
        "zh_tw": ["Clinic", "Stay", "Food"],
        "ko": ["Clinic", "Stay", "Food"],
    },
    "min_length": 2500,
    "schema_type": "MedicalClinic",
}

CONTENT_LANGS = ["en", "ja", "zh", "zh_tw"]


def clean_ai_response(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-z]*\n", "", text)
    text = re.sub(r"\n```$", "", text)
    text = re.sub(r"^(##\s*)?yaml\n", "", text, flags=re.IGNORECASE)
    if "---" in text and not text.startswith("---"):
        text = "---" + text.split("---", 1)[1]
    return text.strip()


def generate_item_article(
    safe_name: str,
    name: str,
    lat: str,
    lng: str,
    address: str,
    lang: str,
    features: str,
    agoda: str = "",
    website: str = "",
    tel: str = "",
    source_image: str = "",
):
    pass  # Claude CLI auth checked in _claude_md


    cats = PROMPT_CONFIG["categories"].get(lang, PROMPT_CONFIG["categories"]["en"])
    cat_list = ", ".join(cats)
    item_type = PROMPT_CONFIG["item_type"] if lang == "en" else PROMPT_CONFIG["item_type_ko"]
    min_len = PROMPT_CONFIG["min_length"]
    source_image = (source_image or "").strip()
    website = (website or "").strip()
    tel = (tel or "").strip()
    agoda = (agoda or "").strip()

    print(f"🚀 [AI] Generating {lang} article: {name}...")

    prompt = f"""
You are an expert travel writer for medical-trip visitors to Korea. Write a careful, SEO-optimized guide for '{name}'.
The article must be at least {min_len} characters, professional, and factual.
Do NOT invent prices, medical outcomes, or doctor credentials.

[Target Info]
- Name: {name}
- Type: {item_type}
- Location: {address}
- Features: {features}
- Language: {lang}

[Categorization Task]
Select the most fitting categories from: [{cat_list}]
(Choose 1-2 that best match the features above)

[Output Format - STRICT]
---
lang: {lang}
title: "Write a clear SEO title mentioning {name}"
lat: {lat}
lng: {lng}
categories: ["Category1"]
thumbnail: "/static/images/{safe_name}.jpg"
address: "{address}"
date: "{datetime.now().strftime('%Y-%m-%d')}"
agoda: "{agoda}"
website: "{website}"
tel: "{tel}"
source_image: "{source_image}"
summary: "Write a 2-3 sentence summary that hooks readers. Keep it on one line."
image_prompt: ""
---

[Article Structure]
## Overview
## Listed details
## Before you book
## Getting there
## Nearby stay & food

IMPORTANT: Do NOT use markdown code blocks. Start directly with '---'.
IMPORTANT: Leave image_prompt empty. Images are fetched separately (TourAPI → Places → default).
"""

    try:
        response_text = _claude_md(prompt)
        final_text = clean_ai_response(response_text)
        os.makedirs(CONTENT_DIR, exist_ok=True)
        filename = f"{safe_name}_{lang}.md"
        with open(os.path.join(CONTENT_DIR, filename), "w", encoding="utf-8") as f:
            f.write(final_text)
        print(f"✅ [Done] {filename} ({len(final_text):,} chars)")
    except Exception as e:
        print(f"❌ [Failed] {name} ({lang}): {e}")


def run_generator(limit: int = 10):
    csv_path = os.path.join(SCRIPT_DIR, "csv", "items.csv")
    if not os.path.exists(csv_path):
        print(f"❌ CSV not found: {csv_path}")
        return

    tasks = []
    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["Name"].strip()
            safe_name = re.sub(r"[^a-z0-9_]", "", name.lower().replace(" ", "_").replace("'", ""))
            source_image = (
                row.get("SourceImage") or row.get("ThumbImage") or row.get("OrgImage") or ""
            ).strip()
            for lang in CONTENT_LANGS:
                out_path = os.path.join(CONTENT_DIR, f"{safe_name}_{lang}.md")
                if not os.path.exists(out_path):
                    tasks.append(
                        (
                            safe_name,
                            name,
                            row.get("Lat", "0"),
                            row.get("Lng", "0"),
                            row.get("Address", "Seoul, Korea"),
                            lang,
                            row.get("Features", ""),
                            row.get("Agoda", ""),
                            row.get("Website", ""),
                            row.get("Tel", ""),
                            source_image,
                        )
                    )
            if len(tasks) >= limit * len(CONTENT_LANGS):
                break

    if not tasks:
        print("✨ No new items to generate.")
        return

    print(f"🔔 Starting generation for {len(tasks)} files...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        ex.map(lambda p: generate_item_article(*p), tasks)


if __name__ == "__main__":
    run_generator(limit=10)
