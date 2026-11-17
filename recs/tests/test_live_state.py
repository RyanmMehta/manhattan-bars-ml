import random

import pytest

from recs import live_state
from recs.live_state import STATE_KEYS

from .conftest import NOW, golden

V = "0370-24-138636"


def rep(age, crowd=3, **kw):
    from datetime import datetime, timedelta
    now = datetime.fromisoformat(NOW)
    r = {"venue_id": V, "scout_id": kw.pop("scout_id", "syn-s-1"), "ts": (now - timedelta(minutes=age)).isoformat(),
         "crowd": crowd, "dancing": None, "line_minutes": None, "cover_usd": None, "music_genre": None,
         "verified_presence": 1, "status": "accepted", "reputation": 0.5, "is_synthetic": 1}
    r.update(kw)
    return r


def test_zero_inputs():
    st = live_state.compute(V, [], [], NOW)
    assert st["n_reports"] == 0 and st["confidence"] == 0.0 and st["display"] == "none"
    assert st["freshness_minutes"] is None and st["trend"] is None and st["vibe_score"] is None
    assert tuple(st) == STATE_KEYS


def test_all_stale_and_future():
    st = live_state.compute(V, [rep(181), rep(-3)], [], NOW)
    assert st["n_reports"] == 0 and st["crowd"] is None


def test_unverified_weight():
    a = live_state.raw_state(V, [rep(0, verified_presence=1)], [], NOW)
    b = live_state.raw_state(V, [rep(0, verified_presence=0)], [], NOW)
    assert b["W_crowd"] == pytest.approx(0.6 * a["W_crowd"])


def test_status_weights():
    a = live_state.raw_state(V, [rep(0)], [], NOW)["W_crowd"]
    assert live_state.raw_state(V, [rep(0, status="disputed")], [], NOW)["W_crowd"] == pytest.approx(0.5 * a)
    for s in ("flagged", "removed"):
        assert live_state.compute(V, [rep(0, status=s)], [], NOW)["n_reports"] == 0
    r = rep(0)
    del r["status"]
    assert live_state.raw_state(V, [r], [], NOW)["W_crowd"] == pytest.approx(a)


def test_missing_reputation_defaults():
    r = rep(0)
    del r["reputation"]
    assert live_state.raw_state(V, [r], [], NOW)["W_crowd"] == pytest.approx(0.625)


def test_thin_field_null():
    # one unverified r=0 report 60 min old: w = 0.25*0.6*0.25 = 0.0375 < 0.30
    st = live_state.compute(V, [rep(60, reputation=0, verified_presence=0, dancing=2)], [], NOW)
    assert st["crowd"] is None and st["dancing"] is None and st["vibe_score"] is None


def test_operator_never_supplies_crowd():
    u = {"venue_id": V, "ts": NOW, "cover_usd": 10, "genres": "house", "dj": None, "crowd": 5, "is_synthetic": 1}
    st = live_state.compute(V, [], [u], NOW)
    assert st["crowd"] is None and st["vibe_score"] is None and st["confidence"] <= 0.25


def test_genre_vote_empty_list_when_none_clear():
    reps = [rep(0, music_genre=g, scout_id=f"s{i}") for i, g in enumerate(["house", "techno", "disco", "pop"])]
    assert live_state.compute(V, reps, [], NOW)["music_genres"] == []


def test_removing_agreeing_report_never_raises_confidence():
    # With agreeing reports, removing one can only lower support. (Removing a *dissenting* report can raise
    # confidence via the agreement term; that is the spec's intent - logged for specs in docs/workstreams.)
    reps = [rep(a, crowd=4, scout_id=f"s{i}") for i, a in enumerate([5, 12, 20, 40])]
    full = live_state.compute(V, reps, [], NOW)["confidence"]
    for i in range(len(reps)):
        assert live_state.compute(V, reps[:i] + reps[i + 1:], [], NOW)["confidence"] <= full + 1e-9


def test_older_duplicate_moves_less():
    g = golden("G1")
    base = live_state.raw_state(V, g["reports"], [], NOW)["crowd"]
    fresh = live_state.raw_state(V, g["reports"] + [rep(0, crowd=1, scout_id="x")], [], NOW)["crowd"]
    old = live_state.raw_state(V, g["reports"] + [rep(90, crowd=1, scout_id="x")], [], NOW)["crowd"]
    assert abs(old - base) < abs(fresh - base)


def test_order_invariance_and_dataframe(fx):
    import pandas as pd
    a = live_state.compute_all(fx["reports"], fx["updates"], NOW)
    rows = fx["reports"].to_dict("records")
    random.Random(1).shuffle(rows)
    b = live_state.compute_all(rows, fx["updates"].to_dict("records"), NOW)
    assert a == b
    assert len(a) == 5
    c = live_state.compute_all(pd.DataFrame(rows), fx["updates"], NOW)
    assert a == c


def test_nan_fields_are_none(fx):
    import json
    for st in live_state.compute_all(fx["reports"], fx["updates"], NOW):
        json.dumps(st, allow_nan=False)


def test_predictor_never_overwrites_or_raises_conf():
    g = golden("G1")
    a = live_state.compute(V, g["reports"], [], NOW)
    b = live_state.compute(V, g["reports"], [], NOW, predictor=lambda vids, ts: [1.0 for _ in vids])
    assert b["predicted_crowd"] == 1.0 and b["predicted_source"] == "model"
    assert {k: v for k, v in b.items() if not k.startswith("predicted")} == \
        {k: v for k, v in a.items() if not k.startswith("predicted")}
    c = live_state.compute(V, g["reports"], [], NOW, predictor=lambda vids, ts: 1 / 0)  # broken model degrades
    assert c["predicted_crowd"] is None


def test_compute_all_includes_venue_ids():
    out = live_state.compute_all([], [], NOW, venue_ids=["a", "b"])
    assert [s["venue_id"] for s in out] == ["a", "b"]


def test_vibe_band():
    assert live_state.vibe_band(34) == "Chill" and live_state.vibe_band(35) == "Lively"
    assert live_state.vibe_band(65) == "Packed" and live_state.vibe_band(None) is None
