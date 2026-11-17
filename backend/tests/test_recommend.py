from sqlalchemy import text

from tests.conftest import login
from tests.fixtures.golden import PREFS

REC_KEYS = {
    "venue_id",
    "name",
    "match_score",
    "vibe_score",
    "confidence",
    "distance_km",
    "reasons",
    "missing",
    "excluded",
    "rank_score",
    "rank",
    "excluded_reason",
    "cluster_label",
    "complaint_risk",
    "is_synthetic",
}


def test_recommend_shape_and_order(client):
    r = client.post("/api/recommend", json=PREFS)
    assert r.status_code == 200 and r.headers["X-Data"] in ("synthetic", "mixed")
    rows = r.json()
    assert len(rows) == 35 and REC_KEYS <= set(rows[0])
    ok = [x for x in rows if not x["excluded"]]
    bad = [x for x in rows if x["excluded"]]
    assert rows == ok + bad
    assert [x["rank_score"] for x in ok] == sorted((x["rank_score"] for x in ok), reverse=True)
    assert [x["rank"] for x in rows] == list(range(1, 36))
    for x in bad:
        assert x["excluded_reason"]
    for x in ok:
        assert x["excluded_reason"] is None
        assert x["complaint_risk"]["label"] == "311 noise-complaint risk"
        exp = round(x["match_score"] * (0.75 + 0.25 * (x["confidence"] or 0)), 1)
        assert abs(x["rank_score"] - exp) < 0.11


def test_unknowns_go_to_missing(client):
    rows = client.post("/api/recommend?now=2026-11-14T19:00:00-05:00", json=PREFS).json()
    assert all(not x["excluded"] or "km" in x["excluded_reason"] for x in rows)
    x = rows[0]
    assert "cover not reported tonight" in x["missing"]
    assert any("no fresh reports" in m for m in x["missing"])


def test_minimal_prefs_ok_and_invalid_422(client):
    assert client.post("/api/recommend", json={}).status_code == 200
    assert client.post("/api/recommend", json={"crowd_pref": 9}).status_code == 422
    assert client.post("/api/recommend", json={"max_distance_km": -1}).status_code == 422


def test_impressions_logged(client):
    u = login(client, "user")
    rows = client.post("/api/recommend", json=PREFS, headers=u["headers"]).json()
    with client.app.state.ctx.db.engine.connect() as c:
        n, users = c.execute(
            text(
                "SELECT COUNT(*), COUNT(DISTINCT user_id) FROM venue_events "
                "WHERE event_type='recommend_impression'"
            )
        ).one()
    assert n == sum(1 for x in rows if not x["excluded"]) and users == 1


def test_plan_night(client):
    r = client.post("/api/plan-night", json=PREFS | {"n_stops": 3})
    assert r.status_code == 200
    stops = r.json()
    assert 1 <= len(stops) <= 3
    keys = {
        "order",
        "venue_id",
        "name",
        "lat",
        "lon",
        "arrive_at",
        "leave_at",
        "walk_minutes_from_prev",
        "distance_km",
        "expected_vibe",
        "match_score",
        "confidence",
        "reasons",
    }
    assert keys <= set(stops[0])
    assert [s["order"] for s in stops] == list(range(1, len(stops) + 1))
    assert len({s["venue_id"] for s in stops}) == len(stops)
    for a, b in zip(stops, stops[1:], strict=False):
        assert a["leave_at"] <= b["arrive_at"]
    assert sum(s["walk_minutes_from_prev"] for s in stops[1:]) <= 30


def test_plan_night_excludes_and_start_time(client):
    first = client.post("/api/plan-night", json=PREFS | {"n_stops": 1}).json()[0]
    again = client.post(
        "/api/plan-night",
        json=PREFS
        | {
            "n_stops": 2,
            "exclude_venue_ids": [first["venue_id"]],
            "start_time": "2026-11-14T22:00:00-05:00",
        },
    ).json()
    assert first["venue_id"] not in {s["venue_id"] for s in again}
    assert again[0]["arrive_at"].startswith("2026-11-14T22:")


def test_plan_night_validation_and_flag(client, make_client):
    assert client.post("/api/plan-night", json={"n_stops": 9}).status_code == 422
    assert client.post("/api/plan-night", json={"start_time": "22:00"}).status_code == 422
    off = make_client(feature_routing=False)
    assert off.post("/api/plan-night", json=PREFS).status_code == 404
