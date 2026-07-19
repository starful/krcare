from flask import Flask, jsonify, render_template, abort, redirect, request, Response, send_from_directory
from flask_compress import Compress
import json, os, frontmatter, markdown, re, glob, hashlib, copy, urllib.parse, urllib.request, io
from datetime import datetime
from urllib.parse import quote

app = Flask(__name__)
Compress(app)

# ==========================================
# ✅ Config import (main customization point)
# ==========================================
try:
    from .config import SITE_CONFIG
except ImportError:
    from config import SITE_CONFIG

try:
    from .reactions import reactions_bp
except ImportError:
    from reactions import reactions_bp

app.register_blueprint(reactions_bp)

SITE_URL = SITE_CONFIG['site_url'].rstrip('/')
GCS_PREFIX = SITE_CONFIG['project_name']
SUPPORTED_LANGS = {'en', 'ja', 'zh', 'zh_tw', 'ko'}
LANG_SUFFIXES = ('zh_tw', 'en', 'ja', 'zh', 'ko')  # longest first for id parsing


def _split_lang_id(item_id: str):
    """Split `tourapi_clinic_zh_tw` → (`tourapi_clinic`, `zh_tw`)."""
    for suf in LANG_SUFFIXES:
        tail = f"_{suf}"
        if item_id.endswith(tail):
            return item_id[: -len(tail)], suf
    return item_id, "en"


def lang_switch_url(target_lang: str) -> str:
    """Same path as current request, with lang swapped (en omits ?lang=)."""
    path = request.path or '/'
    pairs: list[tuple[str, str]] = []
    if target_lang and target_lang != 'en':
        pairs.append(('lang', target_lang))
    for key in request.args:
        if key == 'lang':
            continue
        for value in request.args.getlist(key):
            pairs.append((key, value))
    if not pairs:
        return path
    return f"{path}?{urllib.parse.urlencode(pairs)}"


@app.context_processor
def _inject_lang_switch():
    return {'lang_switch_url': lang_switch_url}


# ==========================================
# Paths
# ==========================================
BASE_DIR    = app.root_path
STATIC_DIR  = os.path.join(BASE_DIR, 'static')
DATA_FILE   = os.path.join(STATIC_DIR, 'json', 'items_data.json')
NEARBY_FILE = os.path.join(STATIC_DIR, 'json', 'nearby_pois.json')
CONTENT_DIR = os.path.join(BASE_DIR, 'content')
GUIDE_DIR   = os.path.join(CONTENT_DIR, 'guides')

GUIDE_IMAGES = SITE_CONFIG['guide_images']


def get_mapped_image(base_id):
    idx = int(hashlib.md5(base_id.encode()).hexdigest(), 16) % len(GUIDE_IMAGES)
    return GUIDE_IMAGES[idx]


def _gcs_image_url(filename):
    return f"https://storage.googleapis.com/ok-project-assets/{GCS_PREFIX}/{filename}"


def _social_image_url(base_id):
    safe = re.sub(r"[^a-z0-9_-]", "", base_id.lower())
    return f"{SITE_URL}/social/{safe}.jpg"


def _og_image_context(base_id):
    return {
        "og_image_abs": _social_image_url(base_id),
        "og_image_width": 1200,
        "og_image_height": 630,
    }


def _card_path(kind, base_id, lang):
    path = f"/card/{kind}/{base_id}"
    if lang == 'ko':
        path += '?lang=ko'
    return path


def _share_context(slug, title, lang, page_path, base_id, kind):
    share_url = f"{SITE_URL}{page_path}"
    share_url_x = f"{SITE_URL}{_card_path(kind, base_id, lang)}"
    site_name = SITE_CONFIG['site_name']
    if lang == 'ko':
        share_tweet = f"{title} — {site_name}"
    else:
        share_tweet = f"{title} — Care guide on {site_name}"
    return {
        "share_id": slug,
        "share_url": share_url,
        "share_url_x": share_url_x,
        "share_tweet": share_tweet,
        "share_lang": lang,
        "og_page_url": share_url,
        "linkedin_inspector_url": f"https://www.linkedin.com/post-inspector/inspect/{quote(share_url, safe='')}",
    }


def _jpeg_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=78, optimize=True, progressive=True)
    return buf.getvalue()


_PLAN_SECTION_TITLES = frozenset({
    "Listed details",
    "Before you book",
    "Visit checklist",
    "Getting there",
    "Nearby stay & food",
})


def _split_md_h2_sections(md_text: str) -> list[tuple[str, str]]:
    """Split markdown into [(heading_or_'', body), ...] by ## headings."""
    text = (md_text or "").strip()
    if not text:
        return []
    parts = re.split(r"(?m)^(## .+)$", text)
    out: list[tuple[str, str]] = []
    if parts and parts[0].strip():
        out.append(("", parts[0].strip()))
    i = 1
    while i < len(parts) - 1:
        heading = parts[i].lstrip("#").strip()
        body = parts[i + 1].strip()
        out.append((heading, body))
        i += 2
    return out


def _parse_md_link(text: str) -> tuple[str, str]:
    m = re.search(r"\[([^\]]+)\]\(([^)]+)\)", text or "")
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return (text or "").strip(), ""


def _format_inline_html(text: str) -> str:
    """Escape text; keep **bold** and bare http(s) links."""
    import html as html_mod

    raw = text or ""
    parts = re.split(r"(\*\*[^*]+\*\*|https?://[^\s<]+)", raw)
    out: list[str] = []
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            out.append(f"<strong>{html_mod.escape(part[2:-2])}</strong>")
        elif part.startswith("http://") or part.startswith("https://"):
            href = html_mod.escape(part.rstrip(".,);"))
            out.append(
                f'<a href="{href}" target="_blank" rel="noopener noreferrer">{href}</a>'
            )
        else:
            out.append(html_mod.escape(part))
    return "".join(out)


def _is_empty_display(value: str) -> bool:
    v = (value or "").strip()
    if not v:
        return True
    low = v.lower()
    markers = (
        "not in public listing",
        "confirm with clinic",
        "ask the clinic",
        "공개정보なし",
        "公開情報なし",
        "公开信息未收录",
        "公開資訊未收錄",
        "클리닉에 문의",
        "クリニックへ確認",
        "请向诊所确认",
        "請向診所確認",
        "데이터 없음",
    )
    return any(m in low or m in v for m in markers)


def _parse_labeled_rows(body: str) -> list[dict]:
    rows = []
    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("- "):
            s = s[2:].strip()
        m = re.match(r"\*\*([^*]+)\*\*\s*:?\s*(.*)$", s)
        if m:
            label = m.group(1).strip().rstrip(":")
            value = m.group(2).strip()
            empty = _is_empty_display(value)
            href = ""
            if not empty:
                if value.startswith("http://") or value.startswith("https://"):
                    href = value
                elif value.startswith("+") or re.match(r"^\d[\d\-\s]+$", value):
                    href = "tel:" + re.sub(r"[\s\-]", "", value)
            rows.append({
                "label": label,
                "text": value,
                "text_html": _format_inline_html(value),
                "href": href,
                "empty": empty,
            })
        else:
            rows.append({
                "label": "",
                "text": s,
                "text_html": _format_inline_html(s),
                "href": "",
                "empty": _is_empty_display(s),
            })
    return rows


def _extract_clinic_plan(md_text: str) -> tuple[str, dict]:
    """Pull structured ## sections into cards; return remnant markdown."""
    sections = _split_md_h2_sections(md_text)
    if not sections:
        return md_text or "", {}

    remnant_parts: list[str] = []
    plan: dict = {}

    for heading, body in sections:
        key = heading.strip()
        if key not in _PLAN_SECTION_TITLES:
            if heading:
                remnant_parts.append(f"## {heading}\n\n{body}".strip())
            elif body:
                remnant_parts.append(body)
            continue

        if key == "Listed details":
            plan["listed"] = {"title": key, "rows": _parse_labeled_rows(body)}

        elif key == "Before you book":
            paras: list[str] = []
            asks: list[str] = []
            for line in body.splitlines():
                s = line.strip()
                if not s:
                    continue
                if s.startswith("- "):
                    asks.append(s[2:].strip())
                else:
                    paras.append(s)
            # Drop the short prompt line that only introduces the list (keep as heading hint)
            prompt = ""
            body_paras = []
            for p in paras:
                low = p.lower()
                if asks and (
                    p.rstrip(":").endswith("about")
                    or "문의" in p
                    or "確認" in p
                    or "确认" in p
                    or "確認：" in p
                    or p.rstrip(":").endswith("：")
                    or "directly about" in low
                    or "ご確認" in p
                ) and len(p) < 80:
                    prompt = p.rstrip(":")
                else:
                    body_paras.append(p)
            plan["before"] = {
                "title": key,
                "paras_html": [_format_inline_html(p) for p in body_paras],
                "prompt": prompt or "",
                "asks": asks,
            }

        elif key == "Visit checklist":
            items = []
            intro = ""
            notes = []
            for line in body.splitlines():
                s = line.strip()
                if not s:
                    continue
                m = re.match(r"^- \[[ xX]?\]\s+(.*)$", s)
                if m:
                    items.append(m.group(1).strip())
                    continue
                if not items and not intro:
                    intro = s
                else:
                    notes.append(s)
            plan["checklist"] = {
                "title": key,
                "intro": intro,
                "checks": items,
                "note": " ".join(notes).strip(),
            }

        elif key == "Getting there":
            plan["getting"] = {"title": key, "rows": _parse_labeled_rows(body)}

        elif key == "Nearby stay & food":
            intro_lines = []
            places = []
            for line in body.splitlines():
                s = line.strip()
                if not s:
                    continue
                if not s.startswith("- "):
                    intro_lines.append(s)
                    continue
                s = s[2:].strip()
                meta = ""
                rest = s
                hm = re.match(r"\*\*([^*]+)\*\*\s*:?\s*(.*)$", s)
                if hm:
                    meta = hm.group(1).strip().rstrip(":")
                    rest = hm.group(2).strip()
                name, href = _parse_md_link(rest)
                tip = ""
                if ")" in rest:
                    after = rest.split(")", 1)[-1].strip()
                    if after.startswith("—") or after.startswith("–") or after.startswith("-"):
                        tip = after.lstrip("—–- ").strip()
                kind = meta.split("·")[0].strip() if meta else "Place"
                places.append({
                    "kind": kind,
                    "meta": meta,
                    "name": name,
                    "href": href,
                    "tip": tip,
                })
            intro_text = " ".join(intro_lines)
            map_href = ""
            map_label = ""
            lm = re.search(r"\[([^\]]+)\]\(([^)]+)\)", intro_text)
            if lm:
                map_label, map_href = lm.group(1), lm.group(2)
                intro_text = re.sub(r"\[[^\]]+\]\([^)]+\)", map_label, intro_text)
            plan["nearby"] = {
                "title": key,
                "intro": intro_text.strip(),
                "map_href": map_href,
                "map_label": map_label,
                "places": places,
            }

    return "\n\n".join(remnant_parts).strip(), plan


def _resolve_item_id(base_id, lang):
    candidate = f"{base_id}_{lang}"
    if os.path.exists(os.path.join(CONTENT_DIR, f"{candidate}.md")):
        return candidate
    fallback = f"{base_id}_en"
    if os.path.exists(os.path.join(CONTENT_DIR, f"{fallback}.md")):
        return fallback
    return None

def _resolve_guide_id(base_id, lang):
    candidate = f"{base_id}_{lang}"
    if os.path.exists(os.path.join(GUIDE_DIR, f"{candidate}.md")):
        return candidate
    fallback = f"{base_id}_en"
    if os.path.exists(os.path.join(GUIDE_DIR, f"{fallback}.md")):
        return fallback
    return None


def _social_source_url(base_id):
    if os.path.exists(os.path.join(GUIDE_DIR, f"{base_id}_en.md")) or os.path.exists(os.path.join(GUIDE_DIR, f"{base_id}_ko.md")):
        return get_mapped_image(base_id)
    return _gcs_image_url(f"{base_id}.jpg")


def _fetch_remote_image(url):
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            raw = resp.read()
            if raw:
                return raw
    except Exception:
        pass
    return None

# ==========================================
# Data loading (startup cache)
# ==========================================
CACHED_DATA   = {SITE_CONFIG['data_key']: [], "last_updated": ""}
CACHED_GUIDES = {lang: [] for lang in ('en', 'ja', 'zh', 'zh_tw', 'ko')}
CACHED_NEARBY = {"anchor": {}, "pois": [], "last_updated": ""}


def load_items():
    global CACHED_DATA
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                CACHED_DATA = json.load(f)
            try:
                from .region import enrich_items_with_regions
            except ImportError:
                from region import enrich_items_with_regions
            enrich_items_with_regions(CACHED_DATA.get(SITE_CONFIG['data_key'], []))
            print(f"✅ Data loaded: {len(CACHED_DATA.get(SITE_CONFIG['data_key'], []))} items")
        except Exception as e:
            print(f"❌ Data load error: {e}")


def load_nearby():
    """Stay/Food POIs near clinics — API-style cards, no detail markdown pages."""
    global CACHED_NEARBY
    if not os.path.exists(NEARBY_FILE):
        print("⚠️  nearby_pois.json not found")
        return
    try:
        with open(NEARBY_FILE, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        if isinstance(raw, list):
            CACHED_NEARBY = {"anchor": {}, "pois": raw, "last_updated": ""}
        elif isinstance(raw, dict):
            pois = raw.get('pois')
            if not isinstance(pois, list):
                pois = []
            CACHED_NEARBY = {
                "anchor": raw.get('anchor') or {},
                "pois": pois,
                "last_updated": raw.get('last_updated') or '',
            }
        else:
            CACHED_NEARBY = {"anchor": {}, "pois": [], "last_updated": ""}
        print(f"✅ Nearby POIs loaded: {len(CACHED_NEARBY.get('pois', []))} places")
    except Exception as e:
        print(f"❌ Nearby load error: {e}")


def _nearby_for_lang(lang: str) -> list[dict]:
    if lang not in SUPPORTED_LANGS:
        lang = 'en'
    out = []
    for poi in CACHED_NEARBY.get('pois', []):
        i18n = (poi.get('i18n') or {})
        loc = i18n.get(lang) or i18n.get('en') or {}
        kind = str(poi.get('kind') or 'Stay')
        out.append({
            "id": poi.get('id'),
            "kind": kind,
            "categories": [kind],
            "lat": poi.get('lat'),
            "lng": poi.get('lng'),
            "thumbnail": poi.get('thumbnail') or '/static/images/default.jpg',
            "tel": (poi.get('tel') or '').strip(),
            "website": (poi.get('website') or '').strip(),
            "source": poi.get('source') or 'nearby',
            "near_clinics": list(poi.get('near_clinics') or []),
            "region": poi.get('region') or '',
            "title": loc.get('title') or poi.get('id'),
            "address": loc.get('address') or '',
            "overview": loc.get('overview') or '',
            "subtype": loc.get('subtype') or '',
            "hours": loc.get('hours') or '',
            "parking": loc.get('parking') or '',
            "transit": loc.get('transit') or '',
            "tips": loc.get('tips') or '',
            "link": None,
            "is_nearby": True,
        })
    return out


def load_guides():
    global CACHED_GUIDES
    if not os.path.exists(GUIDE_DIR):
        return

    all_raw = []
    for fpath in glob.glob(os.path.join(GUIDE_DIR, '*.md')):
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                raw = f.read().strip()
            raw = _clean_md(raw)
            post = frontmatter.loads(raw)
            full_id = os.path.basename(fpath).replace('.md', '')
            base_id, lang_from_id = _split_lang_id(full_id)
            lang = str(post.get('lang') or lang_from_id or 'en')
            if lang not in SUPPORTED_LANGS:
                lang = 'en'
            all_raw.append({
                'base_id': base_id,
                'lang': lang,
                'full_id': full_id,
                'title': str(post.get('title', 'Guide')),
                'summary': str(post.get('summary', '')),
                'date': str(post.get('date', '2026-01-01')),
            })
        except Exception:
            continue

    # Prefer EN order for shared thumbnails; fall back to any lang
    ref = sorted(
        [g for g in all_raw if g['lang'] == 'en'] or all_raw,
        key=lambda x: x['date'],
        reverse=True,
    )
    last_idx = -1
    id_to_img = {}
    for g in ref:
        if g['base_id'] in id_to_img:
            continue
        idx = int(hashlib.md5(g['base_id'].encode()).hexdigest(), 16) % len(GUIDE_IMAGES)
        if idx == last_idx:
            idx = (idx + 1) % len(GUIDE_IMAGES)
        id_to_img[g['base_id']] = GUIDE_IMAGES[idx]
        last_idx = idx

    new_guides = {lang: [] for lang in SUPPORTED_LANGS}
    for g in all_raw:
        new_guides.setdefault(g['lang'], []).append({
            'id': g['full_id'],
            'title': g['title'],
            'summary': g['summary'],
            'thumbnail': id_to_img.get(g['base_id'], GUIDE_IMAGES[0]),
            'published': g['date'],
        })
    for lang in new_guides:
        new_guides[lang].sort(key=lambda x: x['published'], reverse=True)

    CACHED_GUIDES = new_guides
    total = sum(len(v) for v in new_guides.values())
    print(f"✅ Guides loaded: {total}")

def _clean_md(text):
    """Clean common AI output artifacts from markdown."""
    text = re.sub(r'^```[a-z]*\n', '', text)
    text = re.sub(r'\n```$', '', text)
    text = re.sub(r'^(##\s*)?yaml\n', '', text, flags=re.IGNORECASE)
    if '---' in text and not text.startswith('---'):
        text = '---' + text.split('---', 1)[1]
    return text.strip()


_LIST_LINE_RE = re.compile(r'^(\s*)([*+-]|\d+\.)\s+\S')


def _normalize_md_lists(text: str) -> str:
    """Insert blank lines before list blocks so Python-Markdown parses them as lists.

    Gemini (and similar) often writes `paragraph\\n* item` without the blank line
    Markdown requires; without it, markers stay inside a single <p>.
    """
    if not text:
        return text
    lines = text.split('\n')
    out = []
    in_fence = False
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('```'):
            in_fence = not in_fence
            out.append(line)
            continue
        if (
            not in_fence
            and _LIST_LINE_RE.match(line)
            and out
            and out[-1].strip()
            and not _LIST_LINE_RE.match(out[-1])
        ):
            out.append('')
        out.append(line)
    return '\n'.join(out)


def _md_to_html(text: str, extensions=None) -> str:
    """Convert markdown to HTML with list-friendly normalization."""
    if not text:
        return ''
    if extensions is None:
        extensions = ['tables', 'fenced_code']
    return markdown.markdown(_normalize_md_lists(text), extensions=extensions)

def _get_footer_stats(lang):
    items = CACHED_DATA.get(SITE_CONFIG['data_key'], [])
    count = len([i for i in items if i.get('lang') == lang])
    return {
        'total_items':   count if count > 0 else len(items) // 2,
        'last_updated':  CACHED_DATA.get('last_updated', ''),
        'site':          SITE_CONFIG
    }


def _absolute_url(path_or_url):
    if not path_or_url:
        return ""
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url
    return f"{SITE_CONFIG['site_url'].rstrip('/')}/{path_or_url.lstrip('/')}"

# Initial startup load
load_items()
load_nearby()
load_guides()

# ==========================================
# Category mapping
# ==========================================
CATEGORY_MAPPING = SITE_CONFIG.get('category_mapping', {})

# ==========================================
# Routes
# ==========================================
@app.route('/')
def index():
    lang = request.args.get('lang', 'en')
    if lang not in SUPPORTED_LANGS:
        lang = 'en'
    items = CACHED_DATA.get(SITE_CONFIG['data_key'], [])
    initial_items = [i for i in items if i.get('lang') == lang]
    if not initial_items:
        initial_items = [i for i in items if i.get('lang') == 'en']
    initial_items = initial_items[:24]
    top_guides = CACHED_GUIDES.get(lang, [])[:3]
    stats = _get_footer_stats(lang)
    canonical = SITE_CONFIG['site_url'] if lang == 'en' else f"{SITE_CONFIG['site_url']}?lang={lang}"
    maps_lang = {
        'en': 'en',
        'ja': 'ja',
        'zh': 'zh-CN',
        'zh_tw': 'zh-TW',
        'ko': 'ko',
    }.get(lang, 'en')
    return render_template('index.html', lang=lang, guides=CACHED_GUIDES,
                           top_guides=top_guides, initial_items=initial_items,
                           canonical=canonical, maps_lang=maps_lang, **stats)

@app.route('/api/items')
def api_items():
    lang = request.args.get('lang', 'en')
    items = CACHED_DATA.get(SITE_CONFIG['data_key'], [])
    filtered = [i for i in items if i.get('lang') == lang]
    if not filtered:
        filtered = [i for i in items if i.get('lang') == 'en']

    spoofed = []
    for item in filtered:
        s = copy.deepcopy(item)
        s['lang'] = lang
        new_cats = [CATEGORY_MAPPING.get(c.strip(), c.strip()) for c in s.get('categories', [])]
        s['categories'] = list(set(new_cats))
        spoofed.append(s)

    return jsonify({SITE_CONFIG['data_key']: spoofed, "last_updated": CACHED_DATA.get('last_updated')})


@app.route('/api/nearby')
def api_nearby():
    """Stay/Food POIs for map pins — resolved for UI language, no detail pages."""
    lang = request.args.get('lang', 'en')
    if lang not in SUPPORTED_LANGS:
        lang = 'en'
    pois = _nearby_for_lang(lang)
    return jsonify({
        "anchor": CACHED_NEARBY.get('anchor') or {},
        "pois": pois,
        "last_updated": CACHED_NEARBY.get('last_updated') or '',
        "counts": {
            "stay": sum(1 for p in pois if p.get('kind') == 'Stay'),
            "food": sum(1 for p in pois if p.get('kind') == 'Food'),
            "all": len(pois),
        },
    })


@app.route('/guide')
def guide_list():
    lang = request.args.get('lang', 'en')
    if lang not in SUPPORTED_LANGS:
        lang = 'en'
    stats = _get_footer_stats(lang)
    guide_rows = CACHED_GUIDES.get(lang) or CACHED_GUIDES.get('en') or []
    canonical = f"{SITE_CONFIG['site_url']}/guide" if lang == 'en' else f"{SITE_CONFIG['site_url']}/guide?lang={lang}"
    return render_template(
        'guide_list.html',
        guides=CACHED_GUIDES,
        guide_rows=guide_rows,
        lang=lang,
        canonical=canonical,
        **stats,
    )


@app.route('/clinics')
def clinic_list():
    lang = request.args.get('lang', 'en')
    if lang not in SUPPORTED_LANGS:
        lang = 'en'
    sido = (request.args.get('sido') or 'all').strip().lower()
    district = (request.args.get('district') or '').strip().lower() or None
    try:
        page = max(1, int(request.args.get('page', 1)))
    except ValueError:
        page = 1
    per_page = 24

    try:
        from .region import matches_region_filter, parse_region
    except ImportError:
        from region import matches_region_filter, parse_region

    # Prefer parse helpers used by API enrichment
    items = [
        i for i in CACHED_DATA.get(SITE_CONFIG['data_key'], [])
        if i.get('lang') == lang
        and any(str(c).lower() == 'clinic' for c in (i.get('categories') or []))
    ]
    if not items:
        items = [
            i for i in CACHED_DATA.get(SITE_CONFIG['data_key'], [])
            if i.get('lang') == 'en'
            and any(str(c).lower() == 'clinic' for c in (i.get('categories') or []))
        ]

    filtered = []
    for item in items:
        region = item.get('region') or parse_region(item.get('address'), item.get('lat'), item.get('lng'))
        if matches_region_filter(region, sido, district if sido in ('seoul', 'busan') else None):
            row = dict(item)
            row['region'] = region
            filtered.append(row)

    filtered.sort(key=lambda x: str(x.get('title') or ''))
    total = len(filtered)
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, pages)
    start = (page - 1) * per_page
    page_items = filtered[start:start + per_page]

    sido_counts = {'all': len(items)}
    for key in ('seoul', 'busan', 'incheon', 'gyeonggi', 'daegu', 'other'):
        sido_counts[key] = sum(
            1 for i in items
            if (i.get('region') or parse_region(i.get('address'), i.get('lat'), i.get('lng'))).get('sido') == key
        )

    stats = _get_footer_stats(lang)
    qs_base = f"/clinics?lang={lang}" if lang != 'en' else "/clinics"
    canonical = f"{SITE_CONFIG['site_url']}{qs_base}"
    if sido != 'all':
        canonical += f"{'&' if lang != 'en' else '?'}sido={sido}"
    return render_template(
        'clinics.html',
        lang=lang,
        clinics=page_items,
        total=total,
        page=page,
        pages=pages,
        sido=sido,
        district=district,
        sido_counts=sido_counts,
        filter_buttons=SITE_CONFIG.get('filter_buttons', []),
        canonical=canonical,
        **stats,
    )


@app.route('/guide/<guide_id>')
def guide_detail(guide_id):
    path = os.path.join(GUIDE_DIR, f"{guide_id}.md")
    if not os.path.exists(path):
        lang_q = request.args.get('lang', 'en')
        return redirect(f"/guide?lang={lang_q}" if lang_q != 'en' else '/guide')

    with open(path, 'r', encoding='utf-8') as f:
        raw = _clean_md(f.read())
    post  = frontmatter.loads(raw)
    post['id'] = guide_id
    body  = re.sub(r'---.*?---', '', post.content, flags=re.DOTALL)
    body  = body.replace('```markdown', '').replace('```', '').strip()

    title   = str(post.get('title') or guide_id)
    lang    = str(post.get('lang', 'en'))
    base_id, _ = _split_lang_id(guide_id)
    image   = get_mapped_image(base_id)
    stats   = _get_footer_stats(lang)
    alt_en = f"{SITE_CONFIG['site_url']}/guide/{base_id}_en"
    alt_ja = f"{SITE_CONFIG['site_url']}/guide/{base_id}_ja"
    alt_zh = f"{SITE_CONFIG['site_url']}/guide/{base_id}_zh"
    alt_zh_tw = f"{SITE_CONFIG['site_url']}/guide/{base_id}_zh_tw"

    content_html = _md_to_html(body, extensions=['tables', 'toc', 'fenced_code'])
    page_path = f"/guide/{guide_id}"
    share_ctx = _share_context(guide_id, title, lang, page_path, base_id, 'guide')
    return render_template('guide_detail.html',
                           title=title, content=content_html, lang=lang,
                           guide_id=guide_id, base_id=base_id,
                           image_url=image, image_url_abs=_absolute_url(image),
                           canonical=f"{SITE_CONFIG['site_url']}/guide/{guide_id}",
                           alt_en=alt_en, alt_ja=alt_ja, alt_zh=alt_zh, alt_zh_tw=alt_zh_tw,
                           post=post,
                           **_og_image_context(base_id), **share_ctx, **stats)

@app.route('/item/<item_id>')
def item_detail(item_id):
    md_path = os.path.join(CONTENT_DIR, f"{item_id}.md")
    if not os.path.exists(md_path):
        abort(404)

    with open(md_path, 'r', encoding='utf-8') as f:
        raw = _clean_md(f.read())
    post = frontmatter.loads(raw)
    post['id'] = item_id

    if isinstance(post.get('categories'), str):
        post['categories'] = [c.strip() for c in post['categories'].split(',')]

    content_md, plan = _extract_clinic_plan(post.content)
    content_html = _md_to_html(content_md) if content_md else ''
    lang = str(post.get('lang', 'en'))
    base_id, _lang_from_id = _split_lang_id(item_id)
    stats = _get_footer_stats(lang)
    page_path = f"/item/{item_id}"
    share_ctx = _share_context(
        item_id,
        str(post.get('title', item_id)),
        lang,
        page_path,
        base_id,
        'item',
    )
    return render_template(
        'detail.html',
        post=post,
        content=content_html,
        plan=plan,
        base_id=base_id,
        thumbnail_abs=_absolute_url(str(post.get('thumbnail', '/static/images/default.jpg'))),
        **_og_image_context(base_id),
        **share_ctx,
        **stats,
    )


@app.route('/social/<slug>.jpg')
def social_image(slug):
    """Serve thumbnail on-site for OG/Twitter (1200×630 JPEG, no redirect)."""
    safe = re.sub(r"[^a-z0-9_-]", "", slug.lower())
    if not safe:
        abort(404)

    source_urls = [_social_source_url(safe)]
    is_guide = os.path.exists(os.path.join(GUIDE_DIR, f"{safe}_en.md")) or os.path.exists(os.path.join(GUIDE_DIR, f"{safe}_ko.md"))
    if not is_guide:
        source_urls.append(get_mapped_image(safe))

    raw = None
    for source_url in source_urls:
        raw = _fetch_remote_image(source_url)
        if raw:
            break
    if not raw:
        abort(404)

    try:
        from PIL import Image, ImageOps

        img = Image.open(io.BytesIO(raw)).convert("RGB")
        data = _jpeg_bytes(ImageOps.fit(img, (1200, 630), Image.Resampling.LANCZOS))
    except Exception:
        data = raw

    return Response(
        data,
        mimetype="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.route('/card/item/<base_id>')
def item_social_card(base_id):
    lang = request.args.get('lang', 'en').strip().lower()
    if lang not in SUPPORTED_LANGS:
        lang = 'en'
    item_id = _resolve_item_id(base_id, lang)
    if not item_id:
        abort(404)

    md_path = os.path.join(CONTENT_DIR, f"{item_id}.md")
    with open(md_path, 'r', encoding='utf-8') as f:
        post = frontmatter.loads(_clean_md(f.read()))

    title = str(post.get('title', base_id))
    summary = str(post.get('summary', ''))
    page_path = f"/item/{item_id}"
    card_path = _card_path('item', base_id, lang)

    return render_template(
        'social_card.html',
        lang=lang,
        title=title,
        seo_title=f"{title} - {SITE_CONFIG['site_name']}",
        seo_desc=summary,
        site_name=SITE_CONFIG['site_name'],
        page_url=f"{SITE_URL}{page_path}",
        card_url=f"{SITE_URL}{card_path}",
        **_og_image_context(base_id),
    )


@app.route('/card/guide/<base_id>')
def guide_social_card(base_id):
    lang = request.args.get('lang', 'en').strip().lower()
    if lang not in SUPPORTED_LANGS:
        lang = 'en'
    guide_id = _resolve_guide_id(base_id, lang)
    if not guide_id:
        abort(404)

    md_path = os.path.join(GUIDE_DIR, f"{guide_id}.md")
    with open(md_path, 'r', encoding='utf-8') as f:
        post = frontmatter.loads(_clean_md(f.read()))

    title = str(post.get('title', base_id))
    summary = str(post.get('summary', ''))
    page_path = f"/guide/{guide_id}"
    card_path = _card_path('guide', base_id, lang)

    return render_template(
        'social_card.html',
        lang=lang,
        title=title,
        seo_title=f"{title} - {SITE_CONFIG['site_name']} Guide",
        seo_desc=summary,
        site_name=SITE_CONFIG['site_name'],
        page_url=f"{SITE_URL}{page_path}",
        card_url=f"{SITE_URL}{card_path}",
        **_og_image_context(base_id),
    )

# Static assets / SEO
@app.route('/static/images/<path:filename>')
def serve_images(filename):
    """로컬에 파일이 있으면 우선 사용, 없으면 GCS(ok-project-assets/krcare)."""
    image_dir = os.path.join(STATIC_DIR, 'images')
    local_path = os.path.join(image_dir, filename)
    if os.path.exists(local_path):
        return send_from_directory(image_dir, filename)
    project_name = SITE_CONFIG['project_name']
    url = f"https://storage.googleapis.com/ok-project-assets/{project_name}/{filename}"
    if request.query_string:
        url = f"{url}?{request.query_string.decode()}"
    return redirect(url, code=302)

@app.route('/favicon.ico')
@app.route('/favicon-32x32.png')
@app.route('/favicon-48x48.png')
@app.route('/apple-touch-icon.png')
@app.route('/android-chrome-192x192.png')
@app.route('/android-chrome-512x512.png')
def serve_favicons():
    image_dir = os.path.join(STATIC_DIR, 'images')
    filename = request.path[1:]
    if filename == 'favicon.ico':
        for candidate in ('favicon.ico', 'favicons.ico'):
            if os.path.exists(os.path.join(image_dir, candidate)):
                filename = candidate
                break
    local_path = os.path.join(image_dir, filename)
    if os.path.exists(local_path):
        mimetype = 'image/png' if filename.endswith('.png') else 'image/vnd.microsoft.icon'
        return send_from_directory(image_dir, filename, mimetype=mimetype)
    return serve_images(filename)

@app.route('/site.webmanifest')
def webmanifest():
    manifest_path = os.path.join(STATIC_DIR, 'site.webmanifest')
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return Response(f.read(), mimetype='application/manifest+json')
    return Response('{"name":"OK Series","icons":[]}', mimetype='application/manifest+json')

@app.route('/robots.txt')
def robots_txt():
    base = SITE_CONFIG['site_url'].rstrip('/')
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "Disallow: /card/\n"
        "Disallow: /social/\n"
        f"Sitemap: {base}/sitemap.xml\n"
    )
    return Response(content, mimetype='text/plain')


_HREFLANG = {
    'en': 'en',
    'ja': 'ja',
    'zh': 'zh-Hans',
    'zh_tw': 'zh-Hant',
    'ko': 'ko',
}


def _lang_url(path: str, lang: str) -> str:
    """Build absolute URL with ?lang= for non-en list/home pages."""
    base = SITE_CONFIG['site_url'].rstrip('/')
    path = path if path.startswith('/') else f'/{path}'
    if lang == 'en':
        return f"{base}{path}"
    sep = '&' if '?' in path else '?'
    return f"{base}{path}{sep}lang={lang}"


def _sitemap_url_node(loc: str, lastmod: str, alternates: dict | None = None, changefreq: str = 'weekly', priority: str | None = None) -> str:
    parts = [f'<url><loc>{loc}</loc><lastmod>{lastmod}</lastmod><changefreq>{changefreq}</changefreq>']
    if priority:
        parts.append(f'<priority>{priority}</priority>')
    if alternates:
        # Include xhtml alternates + x-default (prefer EN)
        for lang, href in sorted(alternates.items()):
            hl = _HREFLANG.get(lang, lang)
            parts.append(f'<xhtml:link rel="alternate" hreflang="{hl}" href="{href}" />')
        default_href = alternates.get('en') or next(iter(alternates.values()), loc)
        parts.append(f'<xhtml:link rel="alternate" hreflang="x-default" href="{default_href}" />')
    parts.append('</url>')
    return ''.join(parts)


@app.route('/sitemap.xml')
def sitemap_xml():
    base = SITE_CONFIG['site_url'].rstrip('/')
    today = datetime.now().strftime('%Y-%m-%d')
    list_langs = ('en', 'ja', 'zh', 'zh_tw')

    nodes = []

    # Home
    home_alts = {lang: _lang_url('/', lang) for lang in list_langs}
    nodes.append(_sitemap_url_node(home_alts['en'], today, home_alts, priority='1.0'))

    # Guide index + clinics index
    for path, pri in (('/guide', '0.8'), ('/clinics', '0.8')):
        alts = {lang: _lang_url(path, lang) for lang in list_langs}
        nodes.append(_sitemap_url_node(alts['en'], today, alts, priority=pri))

    # Static pages
    for path in ('/about.html', '/contact.html', '/privacy.html'):
        nodes.append(_sitemap_url_node(f'{base}{path}', today, changefreq='monthly', priority='0.3'))

    # Clinic detail pages (all UI langs)
    item_pairs: dict[str, dict[str, str]] = {}
    for item in CACHED_DATA.get(SITE_CONFIG['data_key'], []):
        item_id = item.get('id')
        lang = item.get('lang', 'en')
        if not item_id or lang not in list_langs:
            continue
        base_id, _ = _split_lang_id(item_id)
        item_pairs.setdefault(base_id, {})[lang] = f'{base}/item/{item_id}'
    for pair in item_pairs.values():
        primary = pair.get('en') or next(iter(pair.values()))
        nodes.append(_sitemap_url_node(primary, today, pair, priority='0.6'))

    # Guide detail pages
    guide_pairs: dict[str, dict[str, str]] = {}
    for lang in list_langs:
        for guide in CACHED_GUIDES.get(lang, []):
            gid = guide.get('id')
            if not gid:
                continue
            base_id, _ = _split_lang_id(gid)
            guide_pairs.setdefault(base_id, {})[lang] = f'{base}/guide/{gid}'
    for pair in guide_pairs.values():
        primary = pair.get('en') or next(iter(pair.values()))
        nodes.append(_sitemap_url_node(primary, today, pair, priority='0.7'))

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">'
        + ''.join(nodes)
        + '</urlset>'
    )
    return Response(xml, mimetype='application/xml')

@app.route('/about.html')
def about():
    lang  = request.args.get('lang', 'en')
    stats = _get_footer_stats(lang)
    return render_template('about.html', **stats)

@app.route('/privacy.html')
def privacy():
    return render_template('privacy.html', site=SITE_CONFIG)

@app.route('/contact.html')
@app.route('/contact')
def contact():
    return render_template('contact.html', site=SITE_CONFIG)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
