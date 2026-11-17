import random
from datetime import datetime

from recs import config as C
from recs import live_state, routing

from .conftest import NOW


def _states(fx):
    return live_state.compute_all(fx["reports"], fx["updates"], NOW)


def test_distinct_increasing_and_walk_limit(fx, prefs):
    stops = routing.plan_night(prefs, _states(fx), fx["venues"], NOW, n_stops=3)
    ids = [s["venue_id"] for s in stops]
    assert len(ids) == len(set(ids))
    times = [datetime.fromisoformat(s["arrive_at"]) for s in stops]
    assert times == sorted(times)
    assert sum(s["walk_minutes_from_prev"] for s in stops) <= C.DEFAULT_MAX_TOTAL_WALK_MIN + 0.1
    assert [s["order"] for s in stops] == list(range(1, len(stops) + 1))


def test_fewer_when_infeasible(fx, prefs):
    stops = routing.plan_night(prefs, _states(fx), fx["venues"], NOW, n_stops=10)
    assert len(stops) <= 5
    p = dict(prefs, exclude_venue_ids=list(fx["venues"]["venue_id"]))
    assert routing.plan_night(p, _states(fx), fx["venues"], NOW) == []


def test_closed_at_arrival_is_infeasible(fx, prefs):
    # syn-v-004 closes 23:00 -> never a stop at 23:30
    for s in routing.plan_night(prefs, _states(fx), fx["venues"], NOW, n_stops=4):
        assert s["venue_id"] != "syn-v-004"


def test_local_search_close_to_exhaustive():
    rng = random.Random(42)
    gaps = []
    for case in range(40):
        venues, states = [], []
        for i in range(7):
            vid = f"c{case}-{i}"
            venues.append({"venue_id": vid, "name": vid, "lat": 40.72 + rng.uniform(-0.004, 0.004),
                           "lon": -73.988 + rng.uniform(-0.004, 0.004), "capacity": 100,
                           "genres": rng.choice(["hip-hop", "rock", "house"]), "is_synthetic": 1})
            st = live_state.empty_state(vid)
            st.update(crowd=rng.uniform(1, 5), dancing=rng.uniform(0, 2), line_minutes=rng.choice([0, 5, 10]),
                      confidence=rng.uniform(0, 1), vibe_score=50)
            states.append(st)
        prefs = {"genres": ["hip-hop"], "want_dancing": True, "crowd_pref": 4, "max_line_minutes": 15,
                 "max_distance_km": 1.5, "lat": 40.72, "lon": -73.988, "group_size": 4}
        ctx = routing.build_ctx(prefs, states, venues, NOW)
        cands = routing._candidates(ctx)
        seq = routing.greedy(ctx, cands, 3)
        seq, obj = routing.local_search(ctx, seq, cands, 3)
        _, opt = routing.exhaustive(ctx, cands, 3)
        gaps.append(0.0 if opt <= 0 else (opt - obj) / opt)
    assert sum(g <= 0.05 for g in gaps) / len(gaps) >= 0.9
