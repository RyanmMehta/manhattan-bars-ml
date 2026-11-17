"""HTTP API contract (CONTRACTS "HTTP API" + v2 §G + §J CR-11..14)."""
from __future__ import annotations

import jsonschema
import pytest

from tests.contract import schemas
from tests.contract.constants import DEFAULT_PREFS, DEMO_NOW

NOW = {"now": DEMO_NOW}


def ok(resp, code=200):
    assert resp.status_code == code, f"{resp.request.method} {resp.request.url} -> {resp.status_code}: {resp.text[:300]}"
    return resp.json()


@pytest.fixture(scope="module")
def venues(api):
    return ok(api.get("/api/venues", params={**NOW, "launch_only": "true"}))


@pytest.fixture(scope="module")
def vid(venues):
    return venues[0]["venue_id"]


def login(api, role, **kw):
    body = ok(api.post("/api/auth/demo-login", json={"display_name": f"e2e {role}", "role": role, **kw}))
    jsonschema.validate(body, schemas.LOGIN)
    return {"Authorization": f"Bearer {body['token']}"}


def test_health(api):
    h = ok(api.get("/api/health"))
    jsonschema.validate(h, schemas.HEALTH)
    assert h["recs"] == "real", "backend is running on the recs stub"


def test_venues_list(api, venues):
    r = api.get("/api/venues", params={**NOW, "launch_only": "true"})
    assert r.headers.get("x-data") in {"synthetic", "real", "mixed"}
    assert r.headers.get("x-total-count") is not None
    assert isinstance(venues, list) and len(venues) == 35
    for v in venues:
        jsonschema.validate(v, schemas.VENUE_CARD)
        if v["state"] is not None:
            jsonschema.validate(v["state"], schemas.LIVE_STATE)


def test_venues_limit_and_distance(api):
    vs = ok(api.get("/api/venues", params={**NOW, "limit": 5, "lat": DEFAULT_PREFS["lat"], "lon": DEFAULT_PREFS["lon"]}))
    assert len(vs) == 5
    d = [v["distance_km"] for v in vs]
    assert all(x is not None for x in d) and d == sorted(d)


def test_venue_detail_and_state(api, vid):
    d = ok(api.get(f"/api/venues/{vid}", params=NOW))
    jsonschema.validate(d, schemas.VENUE_DETAIL)
    st = ok(api.get(f"/api/venues/{vid}/state", params=NOW))
    jsonschema.validate(st, schemas.LIVE_STATE)
    assert st["venue_id"] == vid


def test_unknown_venue_404_error_shape(api):
    r = api.get("/api/venues/nope-000", params=NOW)
    assert r.status_code == 404
    jsonschema.validate(r.json(), schemas.ERROR)


def test_validation_error_shape(api):
    r = api.post("/api/recommend", params=NOW, json={"crowd_pref": "lots"})
    assert r.status_code == 422
    jsonschema.validate(r.json(), schemas.ERROR)


def test_recommend(api):
    r = api.post("/api/recommend", params=NOW, json=DEFAULT_PREFS)
    out = ok(r)
    assert r.headers.get("x-data") in {"synthetic", "real", "mixed"}
    for rec in out:
        jsonschema.validate(rec, schemas.RECOMMENDATION)
    shown = [x for x in out if not x["excluded"]]
    assert len(shown) >= 5, f"only {len(shown)} non-excluded venues for default prefs at DEMO_NOW"
    assert all(x["reasons"] for x in shown)
    # excluded venues come after all non-excluded ones
    flags = [x["excluded"] for x in out]
    assert flags == sorted(flags)
    ranks = [x["rank_score"] for x in shown]
    assert ranks == sorted(ranks, reverse=True)


def test_recommend_deterministic(api):
    a = ok(api.post("/api/recommend", params=NOW, json=DEFAULT_PREFS))
    b = ok(api.post("/api/recommend", params=NOW, json=DEFAULT_PREFS))
    assert [x["venue_id"] for x in a] == [x["venue_id"] for x in b]


def test_now_changes_results(api, vid):
    a = ok(api.get(f"/api/venues/{vid}/state", params=NOW))
    b = ok(api.get(f"/api/venues/{vid}/state", params={"now": "2026-11-14T20:05:00-05:00"}))
    c = ok(api.get(f"/api/venues/{vid}/state", params={"now": "2026-11-16T23:30:00-05:00"}))
    assert c["n_reports"] == 0
    assert (a["n_reports"], a["freshness_minutes"]) != (b["n_reports"], b["freshness_minutes"]) or a["n_reports"] == 0


def test_leaderboard_and_bounties(api):
    r = api.get("/api/scouts/leaderboard", params=NOW)
    rows = ok(r)
    assert rows and r.headers.get("x-data")
    for row in rows:
        jsonschema.validate(row, schemas.LEADERBOARD_ROW)
    assert [x["rank"] for x in rows] == sorted(x["rank"] for x in rows)
    b = ok(api.get("/api/bounties", params=NOW))
    for row in b:
        jsonschema.validate(row, schemas.BOUNTY_ROW)


def test_heatmap(api):
    items = ok(api.get("/api/heatmap", params=NOW))
    assert len(items) == 35
    for it in items:
        jsonschema.validate(it, schemas.HEATMAP_ITEM)


def test_plan_night(api):
    r = api.post("/api/plan-night", params=NOW, json={**DEFAULT_PREFS, "n_stops": 3})
    if r.status_code in (404, 501, 503):
        pytest.skip(f"plan-night disabled ({r.status_code}); FEATURE_ROUTING off")
    stops = ok(r)
    stops = stops.get("stops", stops) if isinstance(stops, dict) else stops
    assert len(stops) == 3 and len({s["venue_id"] for s in stops}) == 3
    for s in stops:
        jsonschema.validate(s, schemas.PLAN_STOP)


def test_report_flow_updates_state(api, vid):
    hdr = login(api, "scout")
    before = ok(api.get(f"/api/venues/{vid}/state"))
    r = api.post("/api/reports", headers=hdr, json={"venue_id": vid, "crowd": 5, "dancing": 2, "line_minutes": 5})
    assert r.status_code in (200, 201), r.text
    jsonschema.validate(r.json(), schemas.REPORT_CREATED)
    after = ok(api.get(f"/api/venues/{vid}/state"))
    assert after["n_reports"] == before["n_reports"] + 1
    assert after["freshness_minutes"] is not None and after["freshness_minutes"] <= 1


def test_report_requires_auth(api, vid):
    r = api.post("/api/reports", json={"venue_id": vid, "crowd": 3, "dancing": 0, "line_minutes": 0})
    assert r.status_code in (401, 403)
    jsonschema.validate(r.json(), schemas.ERROR)


def test_owner_flow(api, venues):
    vid = venues[-1]["venue_id"]
    hdr = login(api, "owner", venue_id=vid)
    r = api.post(f"/api/owner/{vid}/updates", headers=hdr,
                 json={"cover_usd": 10, "offer": "$10 cover before midnight", "genres": "hip-hop"})
    assert r.status_code in (200, 201), r.text
    d = ok(api.get(f"/api/venues/{vid}"))
    assert any("10" in str(o) for o in d["offers"]) or d["state"].get("cover_usd") == 10
    own = api.post("/api/reports", headers=hdr, json={"venue_id": vid, "crowd": 5, "dancing": 2, "line_minutes": 0})
    assert own.status_code in (400, 403, 409, 422), "owner reported own venue"
    dash = ok(api.get(f"/api/owner/{vid}/dashboard", params=NOW, headers=hdr))
    jsonschema.validate(dash, schemas.OWNER_DASHBOARD)


def test_feedback(api, vid):
    hdr = login(api, "user")
    r = api.post("/api/feedback", headers=hdr, json={"venue_id": vid, "visited": 1, "rating": 4})
    assert r.status_code in (200, 201), r.text


def test_every_object_has_is_synthetic(api, vid):
    for path in [f"/api/venues/{vid}/state", "/api/scouts/leaderboard", "/api/heatmap"]:
        body = ok(api.get(path, params=NOW))
        for obj in body if isinstance(body, list) else [body]:
            assert "is_synthetic" in obj, path


def test_openapi_has_contract_routes(api):
    spec = ok(api.get("/openapi.json"))
    paths = set(spec["paths"])
    for p in ["/api/health", "/api/venues", "/api/venues/{venue_id}", "/api/venues/{venue_id}/state",
              "/api/reports", "/api/recommend", "/api/plan-night", "/api/scouts/leaderboard", "/api/bounties",
              "/api/owner/{venue_id}/dashboard", "/api/owner/{venue_id}/updates", "/api/heatmap",
              "/api/auth/demo-login", "/api/feedback"]:
        assert p in paths, f"{p} not in /openapi.json"
