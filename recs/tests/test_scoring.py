import copy

from recs import hours, live_state, scoring

from .conftest import NOW, golden


def _g5():
    g = golden("G5")
    st = live_state.compute(g["venue_id"], g["reports"], g["updates"], g["now"])
    return g, st


def test_unknown_never_excludes_and_scores_04():
    g, st = _g5()
    blank = live_state.empty_state(g["venue_id"])
    (r,) = scoring.recommend(g["prefs"], [blank], [dict(g["venue"], genres=None, capacity=None)], NOW)
    assert r["excluded"] is False
    assert "cover not reported tonight" in r["missing"] and "music unknown" in r["missing"]
    # all unknown except distance (known 0.733) -> (0.4*0.85 + 0.15*0.733)/1
    assert r["match_score"] == round(100 * (0.4 * 0.85 + 0.15 * (1 - 0.4 / 1.5)))


def test_removing_info_never_raises_match():
    g, st = _g5()
    (base,) = scoring.recommend(g["prefs"], [st], [g["venue"]], NOW)
    for k in ("crowd", "dancing", "line_minutes", "cover_usd", "music_genres"):
        s2 = dict(st, **{k: None})
        (r,) = scoring.recommend(g["prefs"], [s2], [g["venue"]], NOW)
        assert r["match_score"] <= base["match_score"], k


def test_each_exclusion_rule():
    g, st = _g5()
    p = g["prefs"]
    v = g["venue"]
    cases = [
        (dict(st, line_minutes=30), v, p, "line ~30 min over your 15"),
        (st, dict(v, lat=v["lat"] + 0.05), p, "over your 1.5 km"),
        (st, dict(v, opening_hours="Mo-Su 12:00-20:00"), p, "closed now"),
        (st, dict(v, is_open_now=False), p, "closed now"),
    ]
    for s, ven, pr, txt in cases:
        (r,) = scoring.recommend(pr, [s], [ven], NOW)
        assert r["excluded"] and txt in r["excluded_reason"] and r["rank"] == 1
    assert scoring.recommend(dict(p, exclude_venue_ids=[v["venue_id"]]), [st], [v], NOW) == []
    (r,) = scoring.recommend(p, [st], [dict(v, opening_hours="sunrise-sunset")], NOW)
    assert not r["excluded"]  # unparseable hours never exclude


def test_rank_ordering_and_determinism(fx, prefs):
    states = live_state.compute_all(fx["reports"], fx["updates"], NOW)
    a = scoring.recommend(prefs, states, fx["venues"], NOW)
    b = scoring.recommend(prefs, list(reversed(states)), fx["venues"].iloc[::-1], NOW)
    assert a == b
    inc = [r for r in a if not r["excluded"]]
    assert [r["rank"] for r in a] == list(range(1, len(a) + 1))
    assert all(x["rank_score"] >= y["rank_score"] for x, y in zip(inc, inc[1:]))
    seen_exc = False
    for r in a:
        seen_exc = seen_exc or r["excluded"]
        assert r["excluded"] or not seen_exc


def test_confidence_lifts_rank():
    g, st = _g5()
    hi = scoring.rank_value(80, 1.0)
    lo = scoring.rank_value(80, 0.0)
    assert hi == 80 and lo == 60


def test_null_want_dancing_renormalises():
    g, st = _g5()
    p = dict(g["prefs"], want_dancing=None)
    (r,) = scoring.recommend(p, [st], [g["venue"]], NOW)
    assert "no dancing reports" not in r["missing"]


def test_complaint_risk_never_scored():
    g, st = _g5()
    (a,) = scoring.recommend(g["prefs"], [st], [dict(g["venue"], complaint_risk=0.0)], NOW)
    (b,) = scoring.recommend(g["prefs"], [st], [dict(g["venue"], complaint_risk=1.0)], NOW)
    assert a["match_score"] == b["match_score"] and a["rank_score"] == b["rank_score"] and a["reasons"] == b["reasons"]
    assert b["complaint_risk"] == 1.0


def test_empty_inputs():
    assert scoring.recommend({}, [], [], NOW) == []


def test_hours_parser():
    assert hours.is_open("Mo-Su 18:00-04:00", "2026-11-15T01:00:00-05:00") is True  # Sat night spill
    assert hours.is_open("Mo-Fr 18:00-02:00; Sa,Su off", "2026-11-14T23:30:00-05:00") is False
    assert hours.is_open("24/7", NOW) is True
    assert hours.is_open("Mo-Su 18:00-02:00 || PH off", NOW) is None
    assert hours.is_open(None, NOW) is None
    oh = "Tu-Th 17:00-24:00, Fr-Sa 17:00-02:00, Su 14:00-22:00"
    assert hours.is_open(oh, "2026-11-15T01:30:00-05:00") is True and hours.is_open(oh, "2026-11-15T02:30:00-05:00") is False


def test_reason_copy():
    g, st = _g5()
    (r,) = scoring.recommend(g["prefs"], [st], [g["venue"]], NOW)
    assert r["reasons"][0].startswith("Hip-hop playing (")
    assert len(r["reasons"]) <= 3
    _ = copy
