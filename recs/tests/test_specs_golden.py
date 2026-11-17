"""Specs' golden vectors G1-G8 and differential test vs specs' reference_scoring.py oracle.

Uses docs/specs/ when present (after integration), else the copy in recs/tests/specs_copy/
(copied from origin/nightlife/specs; re-copy when specs changes).
"""
# SYNTHETIC: golden vectors are synthetic test fixtures owned by specs.
import importlib.util
import json
import random
from pathlib import Path

import pytest

from recs import live_state, scoring

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
ROOT = REPO / "docs" / "specs" if (REPO / "docs" / "specs" / "tools" / "reference_scoring.py").exists() else HERE / "specs_copy"
FILES = sorted((ROOT / "golden_synthetic").glob("G*.json"))
STATE_TOL = {"vibe_score": 1, "confidence": 0.01}
REC_TOL = {"match_score": 1, "rank_score": 1, "confidence": 0.01, "vibe_score": 1, "distance_km": 0.01}


def _oracle():
    spec = importlib.util.spec_from_file_location("reference_scoring", ROOT / "tools" / "reference_scoring.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _close(a, b, tol):
    if tol is None or a is None or b is None:
        return a == b
    return abs(a - b) <= tol + 1e-9


def _run(g):
    ids = [v["venue_id"] for v in g.get("venues") or []]
    states = live_state.compute_all(g["reports"], g["updates"], g["now"], venue_ids=ids)
    recs = scoring.recommend(g["prefs"], states, g["venues"], g["now"]) if g.get("prefs") else None
    return states, recs


@pytest.mark.parametrize("path", FILES, ids=[p.stem for p in FILES])
def test_specs_golden(path):
    g = json.loads(path.read_text())
    states, recs = _run(g)
    got = {s["venue_id"]: s for s in states}
    for exp in g["expected"]["states"]:
        s = got[exp["venue_id"]]
        for k, v in exp.items():
            assert _close(s[k], v, STATE_TOL.get(k)), (path.stem, exp["venue_id"], k, s[k], v)
    if g["expected"].get("recommendations") and recs is not None:
        assert [r["venue_id"] for r in recs] == [r["venue_id"] for r in g["expected"]["recommendations"]]
        for r, exp in zip(recs, g["expected"]["recommendations"]):
            for k, v in exp.items():
                assert _close(r[k], v, REC_TOL.get(k)), (path.stem, r["venue_id"], k, r[k], v)


def _random_case(rng, case):
    now = "2026-11-14T23:30:00-05:00"
    from datetime import datetime, timedelta
    t0 = datetime.fromisoformat(now)
    venues, reports, updates = [], [], []
    for i in range(rng.randint(1, 4)):
        vid = f"syn-v-{case}-{i}"
        venues.append({"venue_id": vid, "name": vid, "lat": 40.72 + rng.uniform(-0.01, 0.01),
                       "lon": -73.988 + rng.uniform(-0.01, 0.01), "capacity": rng.choice([None, 40, 120, 300]),
                       "genres": rng.choice([None, "hip-hop|house", "jazz", "r&b"]), "is_synthetic": 1})
        for j in range(rng.randint(0, 6)):
            reports.append({
                "report_id": f"syn-r-{case}-{i}-{j}", "venue_id": vid, "scout_id": f"syn-s-{rng.randint(1, 4)}",
                "ts": (t0 - timedelta(minutes=rng.uniform(-5, 200))).isoformat(),
                "crowd": rng.choice([None, 1, 2, 3, 4, 5]), "dancing": rng.choice([None, 0, 1, 2]),
                "line_minutes": rng.choice([None, 0, 5, 10, 20, 40]), "cover_usd": rng.choice([None, 0, 10, 25]),
                "music_genre": rng.choice([None, "hip-hop", "r&b", "house", "rock"]),
                "verified_presence": rng.choice([0, 1]), "reputation": rng.choice([None, 0.0, 0.5, 0.9]),
                "status": rng.choice(["accepted", "pending", "disputed", "flagged", "removed", None]), "is_synthetic": 1})
        if rng.random() < 0.4:
            updates.append({"update_id": f"syn-u-{case}-{i}", "venue_id": vid,
                            "ts": (t0 - timedelta(minutes=rng.uniform(0, 200))).isoformat(),
                            "cover_usd": rng.choice([None, 0, 15, 30]), "genres": rng.choice([None, "hip-hop|r&b", "house"]),
                            "dj": None, "is_synthetic": 1})
    prefs = {"genres": rng.choice([[], ["hip-hop", "r&b"], ["house"]]), "want_dancing": rng.choice([None, True, False]),
             "crowd_pref": rng.choice([None, 2, 4]), "max_cover_usd": rng.choice([None, 20]),
             "max_line_minutes": rng.choice([None, 15]), "max_distance_km": rng.choice([None, 1.0, 1.5]),
             "lat": 40.7203, "lon": -73.9881, "group_size": rng.choice([None, 2, 6])}
    return now, venues, reports, updates, prefs


def test_differential_vs_reference_oracle():
    ref = _oracle()
    rng = random.Random(42)
    for case in range(500):
        now, venues, reports, updates, prefs = _random_case(rng, case)
        ids = [v["venue_id"] for v in venues]
        ours = live_state.compute_all(reports, updates, now, venue_ids=ids)
        theirs = ref.compute_all(reports, updates, now, venue_ids=ids)
        for a, b in zip(ours, theirs):
            for k, v in b.items():
                assert _close(a[k], v, STATE_TOL.get(k)), (case, k, a[k], v)
        r_ours = scoring.recommend(prefs, ours, venues, now)
        r_theirs = ref.recommend(prefs, theirs, venues, now)
        assert [r["venue_id"] for r in r_ours] == [r["venue_id"] for r in r_theirs], case
        for a, b in zip(r_ours, r_theirs):
            for k, v in b.items():
                if k == "is_synthetic":  # recs also flags synthetic venue attributes (PRD F5); oracle uses state only
                    assert a[k] >= v
                    continue
                assert _close(a[k], v, REC_TOL.get(k)), (case, a["venue_id"], k, a[k], v)


def test_config_matches_specs_parameters():
    from recs import config as C
    from recs.reasons import REASON_MIN_COMPONENT
    P = _oracle().P
    pairs = {
        "H_crowd_min": C.HALF_LIFE_FAST, "H_scout_cover_genre_min": C.HALF_LIFE_SCOUT_SLOW,
        "H_operator_min": C.HALF_LIFE_OPERATOR, "cutoff_age_min": C.CUTOFF_MINUTES, "future_skew_min": C.FUTURE_SKEW_MINUTES,
        "rep_base": C.REP_BASE, "rep_slope": C.REP_SLOPE, "rep_new_scout": C.DEFAULT_REPUTATION,
        "w_unverified": C.UNVERIFIED_WEIGHT, "w_disputed": C.STATUS_WEIGHT["disputed"], "w_operator": C.OPERATOR_WEIGHT,
        "min_field_weight": C.MIN_FIELD_WEIGHT, "genre_share_min": C.GENRE_SHARE_MIN, "conf_k": C.CONF_K,
        "agree_sd_scale": C.AGREE_SD_SCALE, "diverse_single_scout": C.DIVERSE_SINGLE,
        "operator_conf_cap": C.OPERATOR_ONLY_CONF_CAP, "display_show_min": C.DISPLAY_SHOW, "display_low_min": C.DISPLAY_LOW,
        "trend_delta": C.TREND_DELTA, "trend_min_weight": C.TREND_MIN_WEIGHT, "unknown_component": C.UNKNOWN_SCORE,
        "static_genre_score": C.STATIC_GENRE_SCORE, "rank_conf_base": C.RANK_BASE, "rank_conf_slope": C.RANK_CONF,
        "reason_min_component": REASON_MIN_COMPONENT, "line_cap_min": C.LINE_CAP_MINUTES, "dwell_min": C.DEFAULT_DWELL_MIN,
        "vibe_w_crowd": C.VIBE_WEIGHTS["crowd"], "vibe_w_dance": C.VIBE_WEIGHTS["dance"], "vibe_w_line": C.VIBE_WEIGHTS["line"],
        **{f"match_w_{k}": v for k, v in C.MATCH_WEIGHTS.items()},
    }
    for k, v in pairs.items():
        if k in P:
            assert P[k] == pytest.approx(v), k


def test_genres_match_live_sim_copy():
    f = REPO / "simulator" / "config" / "genres.json"
    if not f.exists():
        pytest.skip("simulator/config/genres.json not on this branch")
    from recs import config as C
    data = json.loads(f.read_text())
    slugs = data if isinstance(data, list) else [g["slug"] if isinstance(g, dict) else g for g in data.get("genres", data)]
    assert sorted(slugs) == sorted(C.GENRES)
