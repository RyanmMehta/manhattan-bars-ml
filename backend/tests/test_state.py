from tests.conftest import VENUE, login

STATE_KEYS = {
    "venue_id",
    "crowd",
    "dancing",
    "line_minutes",
    "cover_usd",
    "music_genres",
    "vibe_score",
    "confidence",
    "freshness_minutes",
    "n_reports",
    "trend",
    "sources",
    "is_synthetic",
}


def test_state_shape(client):
    r = client.get(f"/api/venues/{VENUE}/state")
    assert r.status_code == 200
    b = r.json()
    assert STATE_KEYS <= set(b)
    assert b["display"] in ("show", "low", "none")
    assert b["n_reports"] > 0 and b["is_synthetic"] is True


def test_state_before_any_report(client):
    b = client.get(f"/api/venues/{VENUE}/state?now=2026-11-14T19:59:00-05:00").json()
    assert b["n_reports"] == 0 and b["vibe_score"] is None
    assert b["freshness_minutes"] is None and b["display"] == "none"


def test_state_unknown_404(client):
    assert client.get("/api/venues/nope/state").status_code == 404


def test_report_changes_state(client):
    now = "2026-11-14T23:30:00-05:00"
    before = client.get(f"/api/venues/{VENUE}/state?now={now}").json()
    sc = login(client, "scout")
    r = client.post(
        f"/api/reports?now={now}",
        headers=sc["headers"],
        json={"venue_id": VENUE, "crowd": 5, "dancing": 2, "line_minutes": 20},
    )
    assert r.status_code == 201
    after = client.get(f"/api/venues/{VENUE}/state?now={now}").json()
    assert after["n_reports"] == before["n_reports"] + 1
    assert after["freshness_minutes"] == 0


def test_cutoff_ignores_old_reports(client):
    # 4 h after the night ends nothing is within the 180-min cutoff
    b = client.get(f"/api/venues/{VENUE}/state?now=2026-11-15T07:00:00-05:00").json()
    assert b["n_reports"] == 0 and b["vibe_score"] is None
