# KR Care

**Medical trip care in Korea** — discover clinics and medical tourism POIs on a map, with nearby stay and food recommendations powered by TourAPI and Google Places.

| | |
|--|--|
| **Live** | [https://krcare.net](https://krcare.net) |
| **GitHub** | [starful/krcare](https://github.com/starful/krcare) |
| **Hub ID** | `krcare` |

## Features

- Map-based browsing of medical clinics (Korea Tourism API / TourAPI)
- Markdown-driven item pages with frontmatter
- Nearby **stay** and **food** POI cache per clinic (`fetch_nearby_pois.py`)
- No runtime database — compiled JSON + in-memory cache
- GCS-backed static images under `ok-project-assets/krcare/`

## Tech stack

- **Backend:** Python, Flask, Gunicorn, flask-compress
- **Frontend:** Jinja2, vanilla JS, Google Maps
- **Data:** Markdown → `script/build_data.py` → `app/static/json/items_data.json`
- **Infra:** Docker, Cloud Build, Cloud Run (`GCP_PROJECT_ID=starful-258005`)

## OK Admin pipeline

Typical Hub **Content** tab steps:

1. `collect_medical_clinics.py` — TourAPI clinic list (skip-detail mode in pipeline)
2. `fetch_images.py` — Places / asset images
3. `fetch_nearby_pois.py` — stay + food neighbors
4. `optimize_images.py`
5. `build_data.py`

## Local setup

```bash
cd /opt/work/krcare
pip install -r requirements.txt
cp .env.example .env    # TOURAPI_KEY, MAPS_API_KEY, etc.
python3 script/build_data.py
python run.py           # http://localhost:8080
```

Maps key: `KRCARE_GOOGLE_MAPS_API_KEY` (local `.env` or Secret Manager on Cloud Run).

## Deploy

```bash
./deploy.sh --full                      # sync GCS images + generate + build
./deploy.sh --content-only
./deploy.sh --deploy-only --with-deploy
```

Env: `CONTENT_LIMIT`, `GUIDE_LIMIT`, `SERVICE_URL=https://krcare.net`.

## GCS images

- Bucket: `ok-project-assets` · prefix: `krcare/`
- Places search types: `hospital`, `doctor`, `spa`, `lodging`, `restaurant`

## Project structure

```text
krcare/
├── app/
│   ├── __init__.py       # Flask routes, cache
│   ├── config.py         # SITE_CONFIG, categories
│   ├── content/          # Clinic markdown
│   └── static/json/      # Built data
├── script/
│   ├── collect_medical_clinics.py
│   ├── fetch_nearby_pois.py
│   ├── build_data.py
│   └── csv/
├── deploy.sh
└── cloudbuild.yaml
```

## OK Admin

Git: **Ship prep** → **Review & merge** on `main`. Deploy only from production branch.

## Related

- [OK Admin](../okadmin/README.md) · [WORK_ROOT](../README.md)
