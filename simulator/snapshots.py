"""demo_night_snapshots.csv (CONTRACTS v2.2 §J): Live Venue State per venue every 30 min, Sat Nov 14 20:00-03:00.

# SYNTHETIC: values come from synthetic reports; computed with recs.live_state when importable, otherwise the
# simulator's specs §5 fallback (_live_state.py). manifest.json records snapshot_source.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from . import replay, timeutil

DEMO_NIGHT = date(2026, 11, 14)


def snapshot_times(d: date = DEMO_NIGHT) -> pd.DatetimeIndex:
    s, e = timeutil.night_bounds(d)
    return pd.date_range(s, e, freq="30min")  # inclusive both ends: 15 times


def build(tables: dict[str, pd.DataFrame], d: date = DEMO_NIGHT) -> tuple[pd.DataFrame, str]:
    rows, source = [], "fallback"
    for t in snapshot_times(d):
        seen = replay.visible(tables, t)
        states, source = replay.live_states(seen, t)
        for s in states:
            rows.append({"venue_id": s["venue_id"], "snapshot_ts": t, "crowd": s.get("crowd"),
                         "dancing": s.get("dancing"), "line_minutes": s.get("line_minutes"),
                         "vibe_score": s.get("vibe_score"), "confidence": s.get("confidence"),
                         "n_reports": s.get("n_reports", 0), "is_synthetic": 1})
    df = pd.DataFrame(rows).sort_values(["snapshot_ts", "venue_id"], kind="stable").reset_index(drop=True)
    return df, source
