"""Snapshots = the API's view: stored status + CURRENT reputation, via recs.chain.snapshots when importable."""
from __future__ import annotations

import sys
import types

import pandas as pd

import simulator
from simulator import config, snapshots


def _tables():
    return simulator.generate(config.load("small", seed=42, nights=1))


def test_uses_recs_chain_with_api_inputs(monkeypatch):
    t = _tables()
    seen = {}

    def fake_snapshots(reports, updates, start, end, step_minutes=30, venue_ids=None):
        seen.update(reports=reports, updates=updates, start=start, end=end, step=step_minutes, ids=venue_ids)
        return pd.DataFrame([{"venue_id": v, "snapshot_ts": start, "crowd": None, "dancing": None,
                              "line_minutes": None, "vibe_score": None, "confidence": None, "n_reports": 0,
                              "is_synthetic": 1} for v in venue_ids])

    recs = types.ModuleType("recs")
    recs.chain = types.SimpleNamespace(snapshots=fake_snapshots)
    monkeypatch.setitem(sys.modules, "recs", recs)
    df, source = snapshots.build(t)
    assert source == "recs"
    rep = seen["reports"]
    cur = t["syn_scouts"].set_index("scout_id")["reputation"]
    assert (rep["reputation"] == rep["scout_id"].map(cur).fillna(0.5)).all()     # current reputation
    assert list(rep["status"]) == list(t["syn_scout_reports"]["status"])          # stored status, no derived pending
    assert seen["start"] == "2026-11-15T01:00:00+00:00" and seen["end"] == "2026-11-15T08:00:00+00:00"
    assert seen["step"] == 30 and len(seen["ids"]) == 35


def test_fallback_matches_api_inputs(monkeypatch):
    monkeypatch.setitem(sys.modules, "recs", None)  # import recs -> ImportError
    t = _tables()
    df, source = snapshots.build(t)
    assert source == "fallback" and len(df) == 525
    from simulator import _live_state
    rep, _ = snapshots.api_inputs(t)
    now = snapshots.snapshot_times()[7]  # 23:30
    v = df[df["snapshot_ts"] == now].dropna(subset=["vibe_score"]).iloc[0]["venue_id"]
    r = rep[rep["venue_id"] == v].copy()
    r["ts"] = pd.to_datetime(r["ts"], utc=True, format="ISO8601")
    for c in ("crowd", "dancing", "line_minutes", "cover_usd"):
        r[c] = pd.to_numeric(r[c]).astype(float)
    st = _live_state.compute(v, r, None, now)
    row = df[(df["snapshot_ts"] == now) & (df["venue_id"] == v)].iloc[0]
    assert row["vibe_score"] == st["vibe_score"] and row["confidence"] == st["confidence"]


def test_fallback_agrees_with_real_recs():
    """When ml-recs is importable (after integration), the fallback must match it (±1 vibe, ±0.01 conf)."""
    import pytest
    pytest.importorskip("recs.chain")
    t = _tables()
    a, src = snapshots.build(t)
    b, _ = snapshots.build(t, use_recs=False)
    assert src == "recs"
    m = a.merge(b, on=["venue_id", "snapshot_ts"], suffixes=("_r", "_f"))
    assert ((m["vibe_score_r"].fillna(-1) - m["vibe_score_f"].fillna(-1)).abs() <= 1).all()
    assert ((m["confidence_r"].fillna(-9) - m["confidence_f"].fillna(-9)).abs() <= 0.011).all()
