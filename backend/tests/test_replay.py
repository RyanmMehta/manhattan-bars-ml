"""`now` replay across midnight (RULES §8)."""

from tests.conftest import VENUE, login


def test_report_at_2359_seen_at_0010(client):
    sc = login(client, "scout")
    r = client.post(
        "/api/reports?now=2026-11-14T23:59:00-05:00",
        headers=sc["headers"],
        json={"venue_id": VENUE, "crowd": 5, "dancing": 2, "line_minutes": 30},
    )
    assert r.status_code == 201
    st = client.get(f"/api/venues/{VENUE}/state?now=2026-11-15T00:10:00-05:00").json()
    assert st["freshness_minutes"] is not None and st["freshness_minutes"] <= 11
    before = client.get(f"/api/venues/{VENUE}/state?now=2026-11-14T23:58:00-05:00").json()
    after = client.get(f"/api/venues/{VENUE}/state?now=2026-11-15T00:00:00-05:00").json()
    assert after["n_reports"] >= before["n_reports"]


def test_utc_and_offset_now_equivalent(client):
    a = client.get(f"/api/venues/{VENUE}/state?now=2026-11-15T04:30:00Z").json()
    b = client.get(f"/api/venues/{VENUE}/state?now=2026-11-14T23:30:00-05:00").json()
    assert a == b


def test_default_now_is_demo_now(client):
    a = client.get(f"/api/venues/{VENUE}/state").json()
    b = client.get(f"/api/venues/{VENUE}/state?now=2026-11-14T23:30:00-05:00").json()
    assert a == b


def test_owner_dashboard_after_midnight_same_night(client):
    o = login(client, "owner", VENUE)
    b = client.get(
        f"/api/owner/{VENUE}/dashboard?now=2026-11-15T02:00:00-05:00", headers=o["headers"]
    ).json()
    assert b["demand_by_hour"][0]["hour"] == 18 and b["demand_by_hour"][-1]["hour"] == 2


def test_server_clock_when_no_demo_now(make_client):
    c = make_client(demo_now=None)
    assert c.get("/api/health").json()["demo_now"] is None
    st = c.get(f"/api/venues/{VENUE}/state").json()
    assert st["n_reports"] == 0  # the fixture night is in the past
