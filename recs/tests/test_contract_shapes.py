import json
import time

from recs import live_state, routing, scoring
from recs.live_state import STATE_KEYS
from recs.scoring import REC_KEYS

from .conftest import NOW

STOP_KEYS = {"order", "venue_id", "name", "lat", "lon", "arrive_at", "leave_at", "walk_minutes_from_prev",
             "distance_km", "expected_vibe", "match_score", "confidence", "reasons", "is_synthetic"}


def test_state_shape(fx):
    for st in live_state.compute_all(fx["reports"], fx["updates"], NOW):
        assert set(st) == set(STATE_KEYS)
        json.dumps(st, allow_nan=False)
        assert st["vibe_score"] is None or (isinstance(st["vibe_score"], int) and 0 <= st["vibe_score"] <= 100)
        assert 0 <= st["confidence"] <= 1
        assert st["display"] in ("show", "low", "none")
        assert st["trend"] in (None, "rising", "steady", "falling")
        assert st["is_synthetic"] is True


def test_rec_shape(fx, prefs):
    states = live_state.compute_all(fx["reports"], fx["updates"], NOW)
    out = scoring.recommend(prefs, states, fx["venues"], NOW)
    assert len(out) == 5
    for r in out:
        assert set(r) == set(REC_KEYS)
        json.dumps(r, allow_nan=False)
        assert isinstance(r["match_score"], int) and 0 <= r["match_score"] <= 100
        assert isinstance(r["reasons"], list) and isinstance(r["missing"], list)


def test_plan_shape(fx, prefs):
    states = live_state.compute_all(fx["reports"], fx["updates"], NOW)
    stops = routing.plan_night(prefs, states, fx["venues"], NOW, n_stops=3)
    assert 1 <= len(stops) <= 3
    for s in stops:
        assert set(s) == STOP_KEYS
        json.dumps(s, allow_nan=False)


def test_latency_budgets(fx, prefs):
    import random
    rng = random.Random(0)
    venues = [{"venue_id": f"v{i}", "name": f"v{i}", "lat": 40.72 + rng.uniform(-0.006, 0.006),
               "lon": -73.988 + rng.uniform(-0.006, 0.006), "capacity": 100, "is_synthetic": 1} for i in range(35)]
    base = fx["reports"].to_dict("records")
    reports = [dict(base[i % len(base)], venue_id=f"v{i % 35}") for i in range(500)]
    t = time.perf_counter()
    states = live_state.compute_all(reports, [], NOW)
    t_state = time.perf_counter() - t
    t = time.perf_counter()
    scoring.recommend(prefs, states, venues, NOW)
    t_rec = time.perf_counter() - t
    t = time.perf_counter()
    routing.plan_night(prefs, states, venues, NOW)
    t_plan = time.perf_counter() - t
    assert t_state < 0.2 and t_rec < 0.05 and t_plan < 0.3, (t_state, t_rec, t_plan)
