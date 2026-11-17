import importlib.util

import pytest

from app.engine.stub import StubEngine
from tests.fixtures.golden import G1_EXPECTED, G1_REPORTS, G5_EXPECTED, NOW, PREFS, VENUE

HAS_RECS = importlib.util.find_spec("recs") is not None
ENGINES = [StubEngine()]
if HAS_RECS:
    from app.engine.recs_engine import RecsEngine

    ENGINES.append(RecsEngine(None))


def _g5_venue():
    return {
        "venue_id": VENUE,
        "name": "G5",
        "lat": PREFS["lat"] + 0.4 / 111.19,
        "lon": PREFS["lon"],
        "capacity": 120,
        "genres": "",
    }


@pytest.mark.parametrize("engine", ENGINES, ids=lambda e: e.name)
def test_g1(engine):
    s = engine.compute(VENUE, G1_REPORTS, [], NOW)
    assert abs(s["vibe_score"] - G1_EXPECTED["vibe_score"]) <= 1
    assert abs(s["confidence"] - G1_EXPECTED["confidence"]) <= 0.01
    assert s["crowd"] == 3.8 and s["dancing"] == 1.5 and s["line_minutes"] == 10


@pytest.mark.parametrize("engine", ENGINES, ids=lambda e: e.name)
def test_g5(engine):
    s = engine.compute(VENUE, G1_REPORTS, [], NOW) | {"music_genres": ["hip-hop"], "cover_usd": 15}
    r = engine.recommend(PREFS, [s], [_g5_venue()], NOW)[0]
    assert r["match_score"] == G5_EXPECTED["match_score"]
    assert abs(r["rank_score"] - G5_EXPECTED["rank_score"]) <= 1


def test_stub_rules():
    e = StubEngine()
    base = G1_REPORTS[0]
    # future and too-old inputs ignored
    fut = dict(base, ts="2026-11-14T23:40:00-05:00")
    old = dict(base, ts="2026-11-14T20:00:00-05:00")
    assert e.compute(VENUE, [fut, old], [], NOW)["n_reports"] == 0
    # flagged/removed count 0; single scout -> diversity penalty
    flagged = [dict(r, status="flagged") for r in G1_REPORTS]
    assert e.compute(VENUE, flagged, [], NOW)["n_reports"] == 0
    one = [dict(r, scout_id="same") for r in G1_REPORTS]
    assert e.compute(VENUE, one, [], NOW)["confidence"] < G1_EXPECTED["confidence"]
    # operator-only -> vibe null, low confidence, never crowd
    upd = {
        "venue_id": VENUE,
        "ts": "2026-11-14T23:00:00-05:00",
        "cover_usd": 20,
        "genres": "house",
        "is_synthetic": 1,
    }
    s = e.compute(VENUE, [], [upd], NOW)
    assert s["vibe_score"] is None and s["crowd"] is None and s["confidence"] <= 0.25
    assert s["cover_usd"] == 20 and s["music_genres"] == ["house"] and s["display"] == "none"


def test_trend():
    e = StubEngine()

    def mk(age, c, sid):
        ts = f"2026-11-14T{23 if age < 30 else 22}:{(30 - age) % 60:02d}:00-05:00"
        return dict(G1_REPORTS[0], ts=ts, crowd=c, scout_id=sid)

    rising = [mk(5, 5, "a"), mk(10, 5, "b"), mk(40, 2, "c"), mk(45, 2, "d"), mk(50, 2, "e")]
    assert e.compute(VENUE, rising, [], NOW)["trend"] == "rising"
    steady = [dict(r, crowd=3) for r in rising]
    assert e.compute(VENUE, steady, [], NOW)["trend"] == "steady"


@pytest.mark.parametrize("engine", ENGINES, ids=lambda e: e.name)
def test_energy_contradiction_penalty(engine):
    """contracts c3fd169: a confirmed-quiet bar (crowd 1, no dancing) must not outrank a busy one
    for a 'crowd 4, want dancing' group just because line/cover score 1.0; match_score unchanged."""
    quiet = [dict(r, crowd=1, dancing=0, line_minutes=0, cover_usd=0) for r in G1_REPORTS]
    busy = list(G1_REPORTS)
    v_q = _g5_venue() | {"venue_id": "quiet"}
    v_b = _g5_venue()
    s_q = engine.compute("quiet", [dict(r, venue_id="quiet") for r in quiet], [], NOW)
    s_b = engine.compute(VENUE, busy, [], NOW)
    rows = {r["venue_id"]: r for r in engine.recommend(PREFS, [s_q, s_b], [v_q, v_b], NOW)}
    q = rows["quiet"]
    expected_unpenalised = q["match_score"] * (0.75 + 0.25 * (q["confidence"] or 0))
    assert q["rank_score"] < expected_unpenalised * 0.75
    assert rows[VENUE]["rank_score"] > q["rank_score"]
    # unknown crowd/dancing never trigger it
    e = StubEngine()
    empty = e.compute("quiet", [], [], NOW)
    r = e.recommend(PREFS, [empty], [v_q], NOW)[0]
    assert abs(r["rank_score"] - r["match_score"] * 0.75) <= 0.1
