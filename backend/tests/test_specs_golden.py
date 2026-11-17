"""Specs golden vectors G1-G8 (copied test fixture from origin/nightlife/specs
docs/specs/golden_vectors.json @ 008a064). SYNTHETIC: specs' hand-built fixtures."""

import importlib.util
import json
from pathlib import Path

import pytest

from app.engine.stub import StubEngine
from app.timeutil import parse_ts

DATA = json.loads((Path(__file__).parent / "fixtures" / "specs_golden_vectors.json").read_text())
TOL = DATA["tolerance"]
VECTORS = DATA["vectors"]
ENGINES = [StubEngine()]
if importlib.util.find_spec("recs") is not None:
    from app.engine.recs_engine import RecsEngine

    ENGINES.append(RecsEngine(None))

EXACT = [
    "line_minutes",
    "cover_usd",
    "n_reports",
    "display",
    "trend",
    "music_genres",
    "freshness_minutes",
]


def _close(got, exp, tol):
    if exp is None or got is None:
        return got == exp
    return abs(got - exp) <= tol + 1e-9


def _reports(v):
    reps = {s["scout_id"]: s.get("reputation") for s in v.get("scouts") or []}
    return [
        r
        | (
            {"reputation": reps[r["scout_id"]]}
            if "reputation" not in r and reps.get(r["scout_id"]) is not None
            else {}
        )
        for r in v["reports"]
    ]


@pytest.mark.parametrize("engine", ENGINES, ids=lambda e: e.name)
@pytest.mark.parametrize("v", VECTORS, ids=lambda v: v["id"])
def test_states(engine, v):
    now = parse_ts(v["now"])
    for exp in v["expected"]["states"]:
        got = engine.compute(exp["venue_id"], _reports(v), v["updates"], now)
        for k in ("vibe_score", "confidence", "crowd", "dancing"):
            assert _close(got[k], exp[k], TOL[k]), (v["id"], k, got[k], exp[k])
        for k in EXACT:
            assert got[k] == exp[k], (v["id"], k, got[k], exp[k])


@pytest.mark.parametrize("engine", ENGINES, ids=lambda e: e.name)
@pytest.mark.parametrize(
    "v", [x for x in VECTORS if x["expected"]["recommendations"]], ids=lambda v: v["id"]
)
def test_recommendations(engine, v):
    now = parse_ts(v["now"])
    states = [
        engine.compute(s["venue_id"], _reports(v), v["updates"], now)
        for s in v["expected"]["states"]
    ]
    from app.routers.recommend import order_and_rank

    got = {
        r["venue_id"]: r
        for r in order_and_rank(engine.recommend(v["prefs"], states, v["venues"], now))
    }
    order = [r["venue_id"] for r in sorted(got.values(), key=lambda r: r["rank"])]
    assert order == [
        r["venue_id"] for r in sorted(v["expected"]["recommendations"], key=lambda r: r["rank"])
    ]
    for exp in v["expected"]["recommendations"]:
        g = got[exp["venue_id"]]
        assert g["match_score"] == exp["match_score"], (v["id"], g, exp)
        assert _close(g["rank_score"], exp["rank_score"], TOL["rank_score"]), (v["id"], g, exp)
        assert g["excluded"] == exp["excluded"]
        assert bool(g["excluded_reason"]) == bool(exp["excluded_reason"])
        assert set(exp["missing"]) <= set(g["missing"]) or engine.name == "stub", (g, exp)
