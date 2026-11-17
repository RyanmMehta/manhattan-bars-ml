from tests.conftest import VENUE

CARD_KEYS = {
    "venue_id",
    "name",
    "display_name",
    "style",
    "genres",
    "price_level",
    "typical_cover_usd",
    "lat",
    "lon",
    "distance_km",
    "opening_hours",
    "is_claimed",
    "state",
    "complaint_risk",
    "is_synthetic",
}


def test_list_launch_venues(client):
    r = client.get("/api/venues")
    assert r.status_code == 200
    assert r.headers["X-Total-Count"] == "35"
    assert r.headers["X-Data"] == "synthetic"
    body = r.json()
    assert len(body) == 35
    assert CARD_KEYS <= set(body[0])
    names = [c["display_name"].lower() for c in body]
    assert names == sorted(names)
    assert all(c["distance_km"] is None for c in body)


def test_pagination(client):
    r = client.get("/api/venues?limit=10&offset=30")
    assert len(r.json()) == 5 and r.headers["X-Total-Count"] == "35"
    assert client.get("/api/venues?limit=500").status_code == 422


def test_query_and_filters(client):
    r = client.get("/api/venues?q=attaboy").json()
    assert [c["venue_id"] for c in r] == [VENUE]
    assert client.get("/api/venues?q=eldridge").json()  # address match
    assert client.get("/api/venues?style=nonexistent").json() == []
    assert client.get("/api/venues?genre=polka").json() == []
    assert client.get("/api/venues?neighborhood=Mars").json() == []
    some = client.get("/api/venues?genre=hip-hop").json()
    assert some and all("hip-hop" in c["genres"] for c in some)


def test_distance_sort(client):
    r = client.get("/api/venues?lat=40.7203&lon=-73.9881").json()
    d = [c["distance_km"] for c in r]
    assert all(x is not None for x in d) and d == sorted(d)


def test_null_state_not_defaulted(client):
    # 20:05 on the demo night: nothing reported yet for most venues
    body = client.get("/api/venues?now=2026-11-14T19:00:00-05:00").json()
    for c in body:
        st = c["state"]
        assert st["vibe_score"] is None and st["display"] == "none"
        assert st["n_reports"] == 0 and st["freshness_minutes"] is None
        assert st["line_minutes"] is None and st["cover_usd"] is None


def test_launch_only_false(client):
    r = client.get("/api/venues?launch_only=false&limit=5")
    assert r.status_code == 200 and int(r.headers["X-Total-Count"]) >= 35


def test_complaint_risk_label(client):
    c = client.get("/api/venues?q=attaboy").json()[0]
    assert c["complaint_risk"]["label"] == "311 noise-complaint risk"
    assert c["complaint_risk"]["level"] == "high"


def test_detail(client):
    r = client.get(f"/api/venues/{VENUE}")
    assert r.status_code == 200
    b = r.json()
    assert set(b) >= {"venue", "state", "recent_reports", "offers", "is_synthetic"}
    assert len(b["recent_reports"]) <= 10
    ts = [x["ts"] for x in b["recent_reports"]]
    assert ts == sorted(ts, reverse=True)
    for x in b["recent_reports"]:
        assert x["status"] in ("accepted", "pending")
        assert "lat" not in x and "lon" not in x
    for o in b["offers"]:
        assert o["offer"] and o["offer_expires_at"] > o["ts"]


def test_detail_404(client):
    r = client.get("/api/venues/0000-00-000000")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


def test_detail_logs_view_and_state_logs_tap(client):
    from sqlalchemy import text

    client.get(f"/api/venues/{VENUE}")
    client.get(f"/api/venues/{VENUE}/state")
    eng = client.app.state.ctx.db.engine
    with eng.connect() as c:
        types = sorted(r[0] for r in c.execute(text("SELECT event_type FROM venue_events")))
    assert types == ["tap", "view"]


def test_bad_now_422(client):
    assert client.get("/api/venues?now=2026-11-14T23:30:00").status_code == 422
    assert client.get("/api/venues?now=garbage").status_code == 422


def test_manual_attributes_override(make_client, tmp_path):
    p = tmp_path / "manual.csv"
    p.write_text(
        "venue_id,genres,style,has_dance_floor,typical_cover_usd,capacity,price_level,"
        "is_claimed,opening_hours,is_synthetic\n"
        f"{VENUE},jazz,lounge,0,0,40,3,1,,0\n"
    )
    c = make_client(manual_attributes_csv=str(p))
    card = c.get("/api/venues?q=attaboy").json()[0]
    assert card["style"] == "lounge" and card["genres"] == ["jazz"] and card["is_claimed"] is True
