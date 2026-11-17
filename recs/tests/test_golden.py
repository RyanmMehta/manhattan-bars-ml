import pytest

from recs import live_state, scoring

from .conftest import golden


def _check_state(st, exp):
    for k, v in exp.items():
        if k == "confidence":
            assert st[k] == pytest.approx(v, abs=0.01), k
        elif k in ("vibe_score",) and v is not None:
            assert abs(st[k] - v) <= 1, k
        else:
            assert st[k] == v, k


@pytest.mark.parametrize("gid", ["G1", "G2", "G3", "G4", "G7"])
def test_state_vectors(gid):
    g = golden(gid)
    st = live_state.compute(g["venue_id"], g["reports"], g["updates"], g["now"])
    _check_state(st, g["expected"]["state"])


def test_g1_numbers():
    g = golden("G1")
    raw = live_state.raw_state(g["venue_id"], g["reports"], g["updates"], g["now"])
    assert raw["W_crowd"] == pytest.approx(2.2742, abs=1e-3)
    assert raw["crowd"] == pytest.approx(3.76, abs=0.01)
    assert raw["dancing"] == pytest.approx(1.48, abs=0.01)


def test_g5_match():
    g = golden("G5")
    st = live_state.compute(g["venue_id"], g["reports"], g["updates"], g["now"])
    assert st["cover_usd"] == 15 and st["music_genres"] == ["hip-hop"]
    (rec,) = scoring.recommend(g["prefs"], [st], [g["venue"]], g["now"])
    exp = g["expected"]["recommendation"]
    assert abs(rec["match_score"] - exp["match_score"]) <= 1
    assert abs(rec["rank_score"] - exp["rank_score"]) <= 1
    assert rec["rank"] == 1 and rec["excluded"] is False and rec["excluded_reason"] is None


def test_g6_exclusion_known_vs_unknown():
    g = golden("G6")
    states = live_state.compute_all(g["reports"], g["updates"], g["now"])
    recs = {r["venue_id"]: r for r in scoring.recommend(g["prefs"], states, g["venues"], g["now"])}
    for vid, exp in g["expected"]["recommendations"].items():
        r = recs[vid]
        assert r["excluded"] == exp["excluded"]
        assert r["rank"] == exp["rank"]
        if "excluded_reason" in exp:
            assert r["excluded_reason"] == exp["excluded_reason"]
        if "missing_contains" in exp:
            assert exp["missing_contains"] in r["missing"]
    out = scoring.recommend(g["prefs"], states, g["venues"], g["now"])
    assert out[-1]["excluded"] is True  # excluded after included


def test_g8_trend():
    g = golden("G8")
    assert live_state.compute(g["venue_id"], g["reports"], [], g["now"])["trend"] == "rising"
    assert live_state.compute(g["venue_id"], g["reports_falling"], [], g["now"])["trend"] == "falling"
