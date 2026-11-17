from tests.conftest import VENUE, login

NOW = "2026-11-14T23:30:00-05:00"


def test_leaderboard(client):
    r = client.get(f"/api/scouts/leaderboard?now={NOW}&limit=5")
    assert r.status_code == 200 and r.headers["X-Data"] == "synthetic"
    rows = r.json()
    assert len(rows) == 5 and [x["rank"] for x in rows] == [1, 2, 3, 4, 5]
    assert set(rows[0]) == {
        "rank",
        "scout_id",
        "display_name",
        "level",
        "points",
        "points_week",
        "reputation",
        "is_synthetic",
    }
    pts = [x["points"] for x in rows]
    assert pts == sorted(pts, reverse=True)


def test_bounties(client):
    rows = client.get(f"/api/bounties?now={NOW}").json()
    assert rows
    for b in rows:
        assert b["claimed_by"] is None and b["expires_at"] > b["created_at"]
        assert b["venue_name"] and b["is_synthetic"] is True
    assert client.get("/api/bounties?now=2026-11-15T05:00:00-05:00").json() == []


def test_heatmap_now(client):
    r = client.get(f"/api/heatmap?now={NOW}")
    rows = r.json()
    assert r.status_code == 200 and len(rows) == 35
    assert set(rows[0]) == {
        "venue_id",
        "lat",
        "lon",
        "hour",
        "vibe_score",
        "confidence",
        "n_reports",
        "is_synthetic",
    }
    assert all(x["hour"] is None for x in rows)


def test_heatmap_by_hour(client):
    rows = client.get(f"/api/heatmap?by=hour&now={NOW}").json()
    assert sorted({x["hour"] for x in rows}) == [20, 21, 22, 23]
    assert len(rows) == 4 * 35
    full = client.get("/api/heatmap?by=hour&now=2026-11-15T04:00:00-05:00").json()
    assert sorted({x["hour"] for x in full}) == [0, 1, 2, 3, 20, 21, 22, 23]


def test_heatmap_hour_matches_state_at_half_past(client):
    rows = client.get(f"/api/heatmap?by=hour&now={NOW}").json()
    cell = [x for x in rows if x["hour"] == 22 and x["venue_id"] == VENUE][0]
    st = client.get(f"/api/venues/{VENUE}/state?now=2026-11-14T22:30:00-05:00").json()
    assert cell["vibe_score"] == st["vibe_score"] and cell["n_reports"] == st["n_reports"]


def test_heatmap_flag(make_client):
    assert make_client(feature_heatmap=False).get("/api/heatmap").status_code == 404


def test_feedback(client):
    u = login(client, "user")
    client.post("/api/recommend", json={"lat": 40.72, "lon": -73.99}, headers=u["headers"])
    r = client.post(
        "/api/feedback", headers=u["headers"], json={"venue_id": VENUE, "visited": 1, "rating": 5}
    )
    assert r.status_code == 201
    b = r.json()
    assert b["user_id"] == u["user_id"] and b["recommended_at"] == NOW


def test_feedback_auth_and_validation(client):
    body = {"venue_id": VENUE, "visited": 1}
    assert client.post("/api/feedback", json=body).status_code == 401
    sc = login(client, "scout")
    assert client.post("/api/feedback", json=body, headers=sc["headers"]).status_code == 403
    u = login(client, "user")
    h = u["headers"]
    assert client.post("/api/feedback", json=body | {"user_id": "x"}, headers=h).status_code == 403
    assert client.post("/api/feedback", json=body | {"rating": 6}, headers=h).status_code == 422
    assert client.post("/api/feedback", json=body | {"venue_id": "x"}, headers=h).status_code == 404
    r = client.post("/api/feedback", json=body, headers=h)
    assert r.status_code == 201 and r.json()["recommended_at"] is None
