"""
KR Care guide generator — Korea medical-trip guides (EN / JA).

Usage:
  python script/guide_generator.py --force --langs en,ja
  python script/guide_generator.py --limit 4 --force
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import os
import re
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
GUIDE_DIR = os.path.join(BASE_DIR, "app", "content", "guides")

LANG_LABEL = {
    "en": "English",
    "ja": "Japanese",
    "zh": "Simplified Chinese",
    "zh_tw": "Traditional Chinese",
    "ko": "Korean",
}


def clean_ai_response(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-z]*\n", "", text)
    text = re.sub(r"\n```$", "", text)
    text = re.sub(r"^(##\s*)?yaml\n", "", text, flags=re.IGNORECASE)
    if "---" in text and not text.startswith("---"):
        text = "---" + text.split("---", 1)[1]
    return text.strip()


def generate_guide(guide_id: str, topic: str, lang: str, keywords: str) -> None:
    if not API_KEY:
        print("❌ GEMINI_API_KEY is missing")
        return

    try:
        from google import genai

        client = genai.Client(api_key=API_KEY)
    except ImportError:
        print("❌ google-genai package required: pip install google-genai")
        return

    print(f"🚀 [Guide AI] Generating {lang}: {topic}...")

    lang_name = LANG_LABEL.get(lang, lang)
    prompt = f"""
You are a practical editor for KR Care (krcare.net), a map-first medical-trip site for Korea.
Write a high-quality, SEO-friendly guide for international visitors planning clinic / hospital trips to Korea.

[Topic]
- Subject: {topic}
- Output language: {lang_name} ONLY (lang code: {lang})
- SEO keywords: {keywords}

[Output format — STRICT]
---
lang: {lang}
title: "Catchy SEO title in {lang_name}"
date: "{datetime.now().strftime('%Y-%m-%d')}"
summary: "Two compelling sentences on ONE line."
---

[Article requirements]
1. Start after the frontmatter with a short hook (no greeting fluff).
2. Use H2 / H3 headings, bold key terms, bullet lists where useful.
3. Cover concrete steps: booking, language/interpreter, deposits, recovery stay, what to ask the clinic, and red flags.
4. Mention that KR Care map clinics come from official KTO medical-tourism listings; always verify details with the clinic.
5. End with a CTA to use the KR Care map / clinic list.
6. Minimum ~3,500 characters of real content (not placeholder bullets).
7. Do NOT invent specific clinic prices, doctor names, or unverifiable medical claims.
8. Do NOT use markdown code fences. Start directly with '---'.
"""

    try:
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-flash-latest"),
            contents=prompt,
        )
        final_text = clean_ai_response(response.text or "")
        if len(final_text) < 800:
            print(f"⚠️  Short output for {guide_id}_{lang} ({len(final_text)} chars) — keeping anyway")
        os.makedirs(GUIDE_DIR, exist_ok=True)
        filename = f"{guide_id}_{lang}.md"
        path = os.path.join(GUIDE_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(final_text)
        print(f"✅ [Done] {filename} ({len(final_text)} chars)")
    except Exception as e:
        print(f"❌ [Failed] {guide_id} ({lang}): {e}")


def topic_for_lang(row: dict, lang: str) -> str:
    if lang == "ja":
        return (row.get("topic_ja") or row.get("topic_en") or "").strip()
    if lang == "ko":
        return (row.get("topic_ko") or row.get("topic_en") or "").strip()
    if lang in ("zh", "zh_tw"):
        return (row.get(f"topic_{lang}") or row.get("topic_en") or "").strip()
    return (row.get("topic_en") or "").strip()


def run_guide_generator(
    *,
    limit: int = 4,
    langs: list[str] | None = None,
    force: bool = False,
) -> None:
    csv_path = os.path.join(SCRIPT_DIR, "csv", "guides.csv")
    if not os.path.exists(csv_path):
        print(f"❌ CSV not found: {csv_path}")
        return

    langs = langs or ["en", "ja"]
    tasks = []
    guides_touched = 0

    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            guide_id = row["id"].strip()
            keywords = row.get("keywords", "").strip()
            needs = False
            for lang in langs:
                path = os.path.join(GUIDE_DIR, f"{guide_id}_{lang}.md")
                if force or not os.path.exists(path):
                    topic = topic_for_lang(row, lang)
                    if topic:
                        tasks.append((guide_id, topic, lang, keywords))
                        needs = True
            if needs:
                guides_touched += 1
            if guides_touched >= limit:
                break

    if not tasks:
        print("✨ No guides to generate.")
        return

    print(f"🔔 Generating {len(tasks)} guide file(s) (force={force})...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        list(ex.map(lambda p: generate_guide(*p), tasks))


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate KR Care guides")
    ap.add_argument("--limit", type=int, default=4, help="Max guide topics")
    ap.add_argument("--langs", default="en,ja", help="Comma langs, e.g. en,ja")
    ap.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = ap.parse_args()
    langs = [x.strip() for x in args.langs.split(",") if x.strip()]
    run_guide_generator(limit=args.limit, langs=langs, force=args.force)


if __name__ == "__main__":
    main()
