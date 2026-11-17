"""recs/ Python interface (CONTRACTS "Python interface" + v2 §A/§F), incl. golden vectors G1/G5."""
from __future__ import annotations

import json
from datetime import datetime, timedelta

import jsonschema
import pytest

from tests.contract import schemas
from tests.contract.constants import DEFAULT_PREFS, DEMO_NOW, G1, G5, rank_score

VENUE_ID = "0370-24-138636"
NOW = datetime.fromisoformat(DEMO_NOW)


def report(i, age_min, crowd, dancing, line, rep=0.8, genre="hip-hop", **kw):
    r = {
        "report_id": f"syn-r-9{i:05d}", "venue_id": VENUE_ID, "scout_id": f"syn-s-90{i:02d}",
        "ts": (NOW - timedelta(minutes=age_min)).isoformat(), "crowd": crowd, "dancing": dancing,
        "line_minutes": line, "cover_usd": None, "music_genre": genre, "verified_presence": 1,
        "distance_m": 40, "status": "accepted", "reputation": rep, "is_synthetic": 1,
    }
    r.update(kw)
    return r


# SYNTHETIC: specs golden vector G1 (docs/specs/golden_synthetic/G1_normal_four_scouts.json)
G1_REPORTS = [report(1, 5, 4, 2, 10), report(2, 12, 4, 1, 15), report(3, 20, 3, 1, 10), report(4, 40, 4, 2, 5)]


def _call_now(fn, *args):
    """recs may accept datetime or ISO string for `now`; try datetime first."""
    try:
        return fn(*args, NOW)
    except (TypeError, AttributeError):
        return fn(*args, DEMO_NOW)


def test_contract_functions_exist(recs):
    from recs import live_state, routing, scoring
    for mod, name in [(live_state, "compute"), (live_state, "compute_all"), (scoring, "recommend"),
                      (routing, "plan_night")]:
        assert callable(getattr(mod, name, None)), f"recs.{mod.__name__.split('.')[-1]}.{name} missing"


def test_g1_live_state(recs):
    from recs import live_state
    st = _call_now(live_state.compute, VENUE_ID, G1_REPORTS, [])
    jsonschema.validate(st, schemas.LIVE_STATE)
    assert abs(st["vibe_score"] - G1["vibe_score"]) <= 1
    assert abs(st["confidence"] - G1["confidence"]) <= 0.01
    assert st["n_reports"] == 4
    assert st.get("display", "show") == "show"


def test_missing_fields_stay_null(recs):
    from recs import live_state
    st = _call_now(live_state.compute, VENUE_ID, [], [])
    jsonschema.validate(st, schemas.LIVE_STATE)
    assert st["vibe_score"] is None and st["crowd"] is None and st["cover_usd"] is None
    assert st["n_reports"] == 0
    assert st.get("display", "none") == "none"


def test_cutoff_and_future_ignored(recs):
    from recs import live_state
    old = [report(1, 181, 5, 2, 0), report(2, -3, 5, 2, 0)]
    st = _call_now(live_state.compute, VENUE_ID, old, [])
    assert st["n_reports"] == 0 and st["vibe_score"] is None


def test_decay_monotonic(recs):
    from recs import live_state
    fresh = _call_now(live_state.compute, VENUE_ID, [report(1, 5, 4, 1, 10), report(2, 6, 4, 1, 10)], [])
    stale = _call_now(live_state.compute, VENUE_ID, [report(1, 90, 4, 1, 10), report(2, 91, 4, 1, 10)], [])
    assert fresh["confidence"] > stale["confidence"]


def test_g5_match_and_rank(recs):
    from recs import live_state, scoring
    st = _call_now(live_state.compute, VENUE_ID, G1_REPORTS, [])
    st.update({"cover_usd": 15, "music_genres": ["hip-hop"]})
    # 0.4 km from the default prefs point (40.7203, -73.9881), due west-ish.
    venue = {"venue_id": VENUE_ID, "name": "Attaboy", "lat": 40.7203, "lon": -73.99283,
             "capacity": 120, "genres": "hip-hop|r&b", "is_synthetic": 1}
    recs_out = _call_now(scoring.recommend, DEFAULT_PREFS, [st], [venue])
    assert len(recs_out) == 1
    r = recs_out[0]
    jsonschema.validate(r, schemas.RECOMMENDATION)
    assert abs(r["match_score"] - G5["match_score"]) <= 1
    assert abs(r["rank_score"] - rank_score(r["match_score"], r["confidence"])) <= 1
    assert r["rank"] == 1 and r["excluded"] is False and r["reasons"]


def test_exclusion_has_reason(recs):
    from recs import live_state, scoring
    reps = [report(i, 5 + i, 4, 1, 40) for i in range(1, 4)]
    st = _call_now(live_state.compute, VENUE_ID, reps, [])
    venue = {"venue_id": VENUE_ID, "name": "Attaboy", "lat": 40.7203, "lon": -73.9881}
    r = _call_now(scoring.recommend, DEFAULT_PREFS, [st], [venue])[0]
    assert r["excluded"] is True and r["excluded_reason"]


def test_golden_files_if_present(root, recs):
    """Run every specs golden vector (docs/specs/golden_synthetic/G*.json) through recs."""
    from recs import live_state, scoring
    gdir = root / "docs/specs/golden_synthetic"
    files = sorted(gdir.glob("G*.json")) if gdir.exists() else []
    if not files:
        pytest.skip("specs golden vectors not merged")
    checked = 0
    for f in files:
        g = json.loads(f.read_text())
        exp = g.get("expected") or {}
        now = datetime.fromisoformat(g["now"])
        states = []
        for es in exp.get("states") or []:
            vid = es["venue_id"]
            reps = [r for r in g.get("reports", []) if r["venue_id"] == vid]
            ups = [u for u in g.get("updates", []) if u["venue_id"] == vid]
            st = live_state.compute(vid, reps, ups, now)
            states.append(st)
            if es.get("vibe_score") is None:
                assert st["vibe_score"] is None, f"{f.name} {vid}"
            else:
                assert st["vibe_score"] is not None and abs(st["vibe_score"] - es["vibe_score"]) <= 1, f"{f.name} {vid}: {st}"
            if es.get("confidence") is not None:
                assert abs((st["confidence"] or 0) - es["confidence"]) <= 0.01, f"{f.name} {vid}"
            assert st.get("trend") == es.get("trend"), f"{f.name} {vid} trend"
            checked += 1
        if exp.get("recommendations") and g.get("prefs") and g.get("venues"):
            out = {r["venue_id"]: r for r in scoring.recommend(g["prefs"], states, g["venues"], now)}
            for er in exp["recommendations"]:
                got = out[er["venue_id"]]
                assert got["excluded"] == er["excluded"], f"{f.name} {er['venue_id']}"
                if er.get("match_score") is not None and not er["excluded"]:
                    assert abs(got["match_score"] - er["match_score"]) <= 1, f"{f.name} {er['venue_id']}"
    assert checked >= 1


def test_compute_all_on_live_db(recs, live_db):
    import pandas as pd
    from recs import live_state
    reps = pd.read_sql("SELECT r.*, s.reputation FROM syn_scout_reports r JOIN syn_scouts s USING(scout_id) "
                       "WHERE r.ts >= '2026-11-14T20' AND r.ts <= '2026-11-15T03'", live_db)
    ups = pd.read_sql("SELECT * FROM syn_venue_updates WHERE ts >= '2026-11-14T12' AND ts <= '2026-11-15T03'", live_db)
    states = _call_now(live_state.compute_all, reps, ups)
    assert len(states) >= 30
    for st in states:
        jsonschema.validate(st, schemas.LIVE_STATE)
    assert sum(1 for s in states if s["vibe_score"] is not None) >= 10
