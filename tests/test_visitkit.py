"""KR Care visitkit: /events + /hq/api/users."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

# Ensure visitkit package (repo root) is importable when tests run from krcare/
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("VISITLOG_SECRET", "test-visitlog-secret")
os.environ["VISITLOG_DB"] = str(Path("/tmp/krcare-visitlog-test.sqlite3"))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "visitlog.sqlite3"
    monkeypatch.setenv("VISITLOG_SECRET", "test-visitlog-secret")
    monkeypatch.setenv("STORE_BACKEND", "")
    monkeypatch.delenv("STORE_BACKEND", raising=False)
    from visitkit import store, token
    store.configure_store(db_path=db, force=None)
    # reconfigure after import of app
    store._store = None
    store.configure_store(db_path=db)
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    # point store again in case app already configured
    store.configure_store(db_path=db)
    return flask_app.test_client()


def test_events_and_hq_users(client):
    from visitkit.token import hq_token
    r = client.post("/events", json={
        "path": "/", "lang": "ja",
        "events": [{"e": "pv", "p": {"screen": "home"}, "ref": "https://www.google.com/"}],
    })
    assert r.status_code == 200 and r.get_json()["ok"] is True
    assert "sf_vid" in r.headers.getlist("Set-Cookie")[0] or any("sf_vid" in c for c in r.headers.getlist("Set-Cookie"))

    # second event as content + cta with cookie
    vid = None
    for c in r.headers.getlist("Set-Cookie"):
        if c.startswith("sf_vid="):
            vid = c.split(";", 1)[0].split("=", 1)[1]
    assert vid
    client.set_cookie("sf_vid", vid)
    client.post("/events", json={
        "path": "/blog/x", "lang": "ja",
        "events": [
            {"e": "pv", "p": {"screen": "post"}},
            {"e": "affiliate", "p": {"href": "/go/a"}},
        ],
    })

    tok = hq_token("krcare", secret="test-visitlog-secret")
    hq = client.get("/hq/api/users?days=7", headers={"Authorization": f"Bearer {tok}"})
    assert hq.status_code == 200
    data = hq.get_json()
    assert data["kpis"][0]["value"] == 1
    assert data["visitors"]
    assert data["visitors"][0]["steps"]
