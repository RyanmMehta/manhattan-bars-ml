from sqlalchemy import text

from tests.conftest import VENUE, login

NOW = "2026-11-14T23:30:00-05:00"
DOOR = {"lat": 40.71893, "lon": -73.99157}  # Attaboy coordinates


def post(client, headers, now=NOW, **kw):
    body = {"venue_id": VENUE, "crowd": 4, "dancing": 1, "line_minutes": 10} | kw
    return client.post(f"/api/reports?now={now}", json=body, headers=headers)


def test_create_report(client):
    sc = login(client, "scout")
    r = post(client, sc["headers"], **DOOR, cover_usd=10, music_genre="hip-hop")
    assert r.status_code == 201
    b = r.json()
    assert set(b) >= {"report_id", "ts", "status", "points_pending"}
    assert b["status"] == "pending" and b["ts"] == NOW
    assert b["verified_presence"] == 1 and b["distance_m"] == 0
    assert b["points_pending"] >= 15  # base + verified (placeholders)


def test_no_raw_location_stored(client):
    sc = login(client, "scout")
    post(client, sc["headers"], lat=40.72, lon=-73.99)
    with client.app.state.ctx.db.engine.connect() as c:
        cols = [r[1] for r in c.execute(text("PRAGMA table_info(scout_reports)"))]
        row = c.execute(text("SELECT distance_m, verified_presence FROM scout_reports")).one()
    assert "lat" not in cols and "lon" not in cols
    assert row[0] > 150 and row[1] == 0


def test_unverified_without_location(client):
    sc = login(client, "scout")
    b = post(client, sc["headers"]).json()
    assert b["verified_presence"] == 0 and b["distance_m"] is None


def test_validation(client):
    sc = login(client, "scout")
    h = sc["headers"]
    assert post(client, h, crowd=6).status_code == 422
    assert post(client, h, dancing=3).status_code == 422
    assert post(client, h, line_minutes=181).status_code == 422
    assert post(client, h, cover_usd=201).status_code == 422
    assert post(client, h, music_genre="polka").status_code == 422
    assert post(client, h, extra=1).status_code == 422
    assert post(client, h, venue_id="nope").status_code == 404


def test_role_checks(client):
    u = login(client, "user")
    assert post(client, u["headers"]).status_code == 403
    o = login(client, "owner", VENUE)
    r = post(client, o["headers"])
    assert r.status_code == 403 and "own venue" in r.json()["error"]["message"]


def test_rate_limit(client):
    sc = login(client, "scout")
    assert post(client, sc["headers"]).status_code == 201
    assert post(client, sc["headers"], now="2026-11-14T23:40:00-05:00").status_code == 429
    assert post(client, sc["headers"], now="2026-11-14T23:46:00-05:00").status_code == 201


def test_bounty_claim(client):
    bounties = client.get(f"/api/bounties?now={NOW}").json()
    b = bounties[0]
    v = client.get(f"/api/venues/{b['venue_id']}").json()["venue"]
    sc = login(client, "scout")
    r = post(client, sc["headers"], venue_id=b["venue_id"], lat=v["lat"], lon=v["lon"])
    assert r.status_code == 201
    assert r.json()["points_pending"] >= 15 + b["points"]
    left = {x["bounty_id"] for x in client.get(f"/api/bounties?now={NOW}").json()}
    assert b["bounty_id"] not in left
    board = client.get(f"/api/scouts/leaderboard?limit=100&now={NOW}").json()
    me = [x for x in board if x["scout_id"] == sc["scout_id"]][0]
    assert me["points"] == r.json()["points_pending"] == me["points_week"]
    assert me["is_synthetic"] is False


def test_write_time_is_demo_now_without_override(make_client):
    c = make_client(allow_write_now=False)
    sc = login(c, "scout")
    b = c.post(
        "/api/reports?now=2026-11-14T21:00:00-05:00",
        headers=sc["headers"],
        json={"venue_id": VENUE, "crowd": 3, "dancing": 0, "line_minutes": 0},
    ).json()
    assert b["ts"] == NOW  # `now` ignored on writes unless ALLOW_WRITE_NOW=1
