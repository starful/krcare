import os
from pathlib import Path

from dotenv import load_dotenv

# Load local .env before reading SITE_CONFIG (dev / local only)
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# ============================================================
#  ✅ KR Care core config
# ============================================================

SITE_CONFIG = {

    # ----------------------------------------------------------
    # 1. Basic identity
    # ----------------------------------------------------------
    "project_name":  "krcare",
    "site_name":     "KR Care",
    "site_url":      os.getenv("SITE_URL", "https://krcare.net"),
    "tagline":       "Medical trip care in Korea",
    "data_key":      "items",

    # ----------------------------------------------------------
    # 2. SEO / analytics
    # ----------------------------------------------------------
    "ga_id":         os.getenv("GA_ID", "G-8FYGGKZ1ST"),
    # Maps JS key: Cloud secret name is KRCARE_GOOGLE_MAPS_API_KEY
    "maps_api_key":  (
        os.getenv("MAPS_API_KEY")
        or os.getenv("KRCARE_GOOGLE_MAPS_API_KEY")
        or ""
    ),
    # Cloud map style "krcare"
    "maps_id":       os.getenv("MAPS_ID", "2938bb3f7f034d78a92f600c"),

    # ----------------------------------------------------------
    # 3. Icon & theme
    # ----------------------------------------------------------
    "emoji":         "💚",
    "accent_color":  "#2EB5A8",
    "bg_dot_color":  "#A8D4CE",

    # ----------------------------------------------------------
    # 4. Header filter buttons (two-level region: sido → district)
    # Labels duplicated in JS (regions.js) for dynamic district row.
    # ----------------------------------------------------------
    "filter_buttons": [
        {"label": "All",      "theme": "all",      "count_id": "count-sido-all"},
        {"label": "Seoul",    "theme": "seoul",    "count_id": "count-sido-seoul"},
        {"label": "Busan",    "theme": "busan",    "count_id": "count-sido-busan"},
        {"label": "Incheon",  "theme": "incheon",  "count_id": "count-sido-incheon"},
        {"label": "Gyeonggi", "theme": "gyeonggi", "count_id": "count-sido-gyeonggi"},
        {"label": "Daegu",    "theme": "daegu",    "count_id": "count-sido-daegu"},
        {"label": "Other",    "theme": "other",    "count_id": "count-sido-other"},
    ],

    # ----------------------------------------------------------
    # 5. Category mapping (source -> UI label)
    # ----------------------------------------------------------
    "category_mapping": {
        "Clinic": "Clinic",
        "Stay": "Stay",
        "Food": "Food",
    },

    # ----------------------------------------------------------
    # 6. JS category map (used by main.js)
    # ----------------------------------------------------------
    "js_category_map": {
        "clinic": "Clinic",
        "stay": "Stay",
        "food": "Food",
    },

    # ----------------------------------------------------------
    # 7. Detail page schema type (JSON-LD)
    # ----------------------------------------------------------
    "schema_type": "MedicalClinic",

    # ----------------------------------------------------------
    # 8. Guide section images
    # ----------------------------------------------------------
    "guide_images": [
        "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?q=80&w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1631217868264-e5b90bb7e133?q=80&w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1566073771259-6a8506099945?q=80&w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1559339352-11d035aa65de?q=80&w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?q=80&w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?q=80&w=800&auto=format&fit=crop",
    ],

    # ----------------------------------------------------------
    # 9. Affiliate (same Klook short link as krcampus)
    # ----------------------------------------------------------
    "klook_url": "https://klook.tpo.mx/ED7IfKaq",

    # ----------------------------------------------------------
    # 10. Footer
    # ----------------------------------------------------------
    "footer_tagline":  "Medical trip care in Korea.",
    "footer_year":     "2026",
}
