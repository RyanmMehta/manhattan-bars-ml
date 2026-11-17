"""INCLUDE_SYNTHETIC=0 must not 500 any endpoint and must hide synthetic rows."""

import pytest

from tests.conftest import VENUE, login
from tests.fixtures.golden import PREFS


@pytest.fixture
def real(make_client):
    return make_client(include_synthetic=False)


def test_reads_work_and_are_real(real):
    for url in [
        "/api/health",
        "/api/venues",
        f"/api/venues/{VENUE}",
        f"/api/venues/{VENUE}/state",
        "/api/scouts/leaderboard",
        "/api/bounties",
        "/api/heatmap",
        "/api/heatmap?by=hour",
    ]:
        r = real.get(url)
        assert r.status_code == 200, url
        if isinstance(r.json(), list):
            assert r.headers.get("X-Data") == "real", url
    assert real.get("/api/bounties").json() == []
    assert real.get("/api/scouts/leaderboard").json() == []
    assert all(c["state"]["n_reports"] == 0 for c in real.get("/api/venues").json())
    assert all(c["is_synthetic"] is False for c in real.get("/api/venues").json())


def test_posts_work(real):
    assert real.post("/api/recommend", json=PREFS).status_code == 200
    assert real.post("/api/plan-night", json=PREFS).status_code == 200
    sc = login(real, "scout")
    r = real.post(
        "/api/reports",
        headers=sc["headers"],
        json={"venue_id": VENUE, "crowd": 4, "dancing": 1, "line_minutes": 5},
    )
    assert r.status_code == 201
    st = real.get(f"/api/venues/{VENUE}/state").json()
    assert st["n_reports"] == 1 and st["is_synthetic"] is False
    o = login(real, "owner", VENUE)
    d = real.get(f"/api/owner/{VENUE}/dashboard", headers=o["headers"]).json()
    assert d["is_synthetic"] is False and d["reports_tonight"] == 1
    board = real.get("/api/scouts/leaderboard").json()
    assert [x["scout_id"] for x in board] == [sc["scout_id"]]
