from sqlalchemy import text

from tests.conftest import VENUE, login
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
        assert x["rank_score"] <= exp + 0.11  # energy penalty may only lower it (c3fd169)
        assert x["rank_score"] >= exp * 0.5 - 0.11


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


def test_null_rank_from_engine_is_assigned(client, monkeypatch):
    eng = client.app.state.ctx.engine
    real = eng.recommend

    def null_ranks(*a):
        rows = real(*a)
        for r in rows:
            if r["excluded"]:
                r["rank"] = None
        return rows[::-1]

    monkeypatch.setattr(eng, "recommend", null_ranks)
    rows = client.post("/api/recommend", json=PREFS).json()
    assert [x["rank"] for x in rows] == list(range(1, len(rows) + 1))
    flags = [x["excluded"] for x in rows]
    assert flags == sorted(flags)


def test_numeric_complaint_risk_from_engine(client, monkeypatch):
    """Final recs returns complaint_risk as a float; it must not knock /recommend onto the stub."""
    eng = client.app.state.ctx.engine
    real = eng.recommend

    def with_float(*a):
        rows = real(*a)
        for r in rows:
            r["complaint_risk"] = 0.6
            r["reasons"] = ["engine-marker"]
        return rows

    monkeypatch.setattr(eng, "recommend", with_float)
    rows = client.post("/api/recommend", json=PREFS).json()
    assert rows[0]["reasons"] == ["engine-marker"]  # engine output used, not the stub's
    cr = rows[0]["complaint_risk"]
    assert cr["label"] == "311 noise-complaint risk" and cr["score"] == 0.6


def test_exclude_venue_ids_dropped(client):
    rows = client.post("/api/recommend", json=PREFS | {"exclude_venue_ids": [VENUE]}).json()
    assert len(rows) == 34 and VENUE not in {r["venue_id"] for r in rows}


def test_rows_carry_card_and_state_fields(client):
    rows = client.post("/api/recommend", json=PREFS).json()
    cards = {c["venue_id"]: c for c in client.get("/api/venues").json()}
    for r in rows:
        c = cards[r["venue_id"]]
        assert r["display_name"] == c["display_name"]
        assert r["freshness_minutes"] == c["state"]["freshness_minutes"]
        assert r["n_reports"] == c["state"]["n_reports"]
    assert any(r["n_reports"] > 0 and r["freshness_minutes"] is not None for r in rows)
