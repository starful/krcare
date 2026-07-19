"""Share bar and social card regression tests."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from __init__ import app as flask_app  # noqa: E402


@pytest.fixture()
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def test_item_detail_has_share_bar(client):
    r = client.get("/item/sample_item_1_en")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "share-bar" in html
    assert "share-btn-x" in html
    assert "/social/sample_item_1.jpg" in html
    assert "card/item/sample_item_1" in html
    assert 'name="twitter:image"' in html
    assert "?v=" not in html.split('name="twitter:image"')[1][:120]


def test_guide_detail_has_share_bar(client):
    r = client.get("/guide/guide_001_en")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "share-bar" in html
    assert "/social/guide_001.jpg" in html
    assert "card/guide/guide_001" in html


def test_social_image_item(client):
    r = client.get("/social/sample_item_1.jpg")
    assert r.status_code == 200
    assert r.headers.get("Content-Type", "").startswith("image/jpeg")
    assert len(r.get_data()) > 500

    head = client.head("/social/sample_item_1.jpg")
    assert head.status_code == 200


def test_social_image_guide(client):
    r = client.get("/social/guide_001.jpg")
    assert r.status_code == 200
    assert r.headers.get("Content-Type", "").startswith("image/jpeg")
    assert len(r.get_data()) > 500


def test_item_social_card_page(client):
    r = client.get("/card/item/sample_item_1")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'property="og:url" content="https://oktemplate.net/card/item/sample_item_1"' in html
    assert "/social/sample_item_1.jpg" in html
    assert "View page" in html


def test_guide_social_card_page(client):
    r = client.get("/card/guide/guide_001")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'property="og:url" content="https://oktemplate.net/card/guide/guide_001"' in html
    assert "/social/guide_001.jpg" in html
