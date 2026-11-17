"""demo_night_snapshots.csv (CONTRACTS v2.2 §J): Live Venue State per venue every 30 min, Sat Nov 14 20:00-03:00.

Canonical snapshot = the API's view (master decision, Nov 17): stored report `status` and CURRENT
`syn_scouts.reputation`, exactly the inputs backend passes to recs. When `recs` is importable this calls
`recs.chain.snapshots(...)`; otherwise it uses the simulator's specs §5 mirror on the same inputs.
manifest.json records snapshot_source (recs|fallback).
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from . import io, timeutil

DEMO_NIGHT = date(2026, 11, 14)


def snapshot_times(d: date = DEMO_NIGHT) -> pd.DatetimeIndex:
    s, e = timeutil.night_bounds(d)
    return pd.date_range(s, e, freq="30min")  # inclusive both ends: 15 times


def api_inputs(tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """What backend hands recs: stored reports joined to current reputation (default 0.5), and updates
    (output format: local ISO timestamps, as in live_sim.db)."""
    rep = io.to_output(tables["syn_scout_reports"], "syn_scout_reports")
    cur = tables["syn_scouts"].set_index("scout_id")["reputation"]
    rep["reputation"] = rep["scout_id"].map(cur).fillna(0.5).astype(float)
    upd = io.to_output(tables["syn_venue_updates"], "syn_venue_updates")
    return rep, upd


def _via_recs(rep, upd, times, venue_ids) -> pd.DataFrame:
    from recs import chain  # type: ignore  # ml-recs; raises ImportError when absent
    df = chain.snapshots(rep, upd, times[0].isoformat(), times[-1].isoformat(), step_minutes=30,
                         venue_ids=venue_ids)
    df["snapshot_ts"] = pd.to_datetime(df["snapshot_ts"], utc=True, format="ISO8601")
    return df


def _via_fallback(rep, upd, times, venue_ids) -> pd.DataFrame:
    # SYNTHETIC: mirror of specs §5 (_live_state.py); used only when recs is not importable.
    from . import _live_state
    r = rep.copy()
    r["ts"] = pd.to_datetime(r["ts"], utc=True, format="ISO8601")
    for c in ("crowd", "dancing", "line_minutes", "cover_usd"):
        r[c] = pd.to_numeric(r[c], errors="coerce").astype(float)
    by_v = dict(tuple(r.groupby("venue_id")))
    u = upd.assign(ts=pd.to_datetime(upd["ts"], utc=True, format="ISO8601"))
    u_by_v = dict(tuple(u.groupby("venue_id")))
    sp = _live_state.SPEC
    rows = []
    for t in times:
        for v in venue_ids:
            s = _live_state.compute(v, by_v.get(v), None, t)
            if s["confidence"] is None:  # specs §5.6 operator-only rule: conf = min(0.25, 0.25·Σw); none -> 0.0
                g = u_by_v.get(v)
                w = 0.0
                if g is not None:
                    age = (t - g["ts"]).dt.total_seconds() / 60
                    ok = (age >= -sp["skew_minutes"]) & (age <= sp["cutoff_minutes"])
                    w = float((sp["w_operator"] * 0.5 ** (age[ok].clip(lower=0) / sp["half_life_operator"])).sum())
                s["confidence"] = round(min(0.25, 0.25 * w), 2)
            rows.append({"venue_id": v, "snapshot_ts": t, "crowd": s["crowd"], "dancing": s["dancing"],
                         "line_minutes": s["line_minutes"], "vibe_score": s["vibe_score"],
                         "confidence": s["confidence"], "n_reports": s["n_reports"], "is_synthetic": 1})
    return pd.DataFrame(rows)


def build(tables: dict[str, pd.DataFrame], d: date = DEMO_NIGHT, use_recs: bool = True) -> tuple[pd.DataFrame, str]:
    rep, upd = api_inputs(tables)
    times = snapshot_times(d)
    vids = sorted(tables["syn_venue_attributes"]["venue_id"])
    df, source = None, "fallback"
    if use_recs:
        try:
            df, source = _via_recs(rep, upd, times, vids), "recs"
        except ImportError:
            df = None
    if df is None:
        df = _via_fallback(rep, upd, times, vids)
    df["is_synthetic"] = 1
    df = df.sort_values(["snapshot_ts", "venue_id"], kind="stable").reset_index(drop=True)
    return df, source
