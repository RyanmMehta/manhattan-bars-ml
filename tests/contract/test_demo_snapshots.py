"""data/synthetic_live/demo_night_snapshots.csv (v2.2 §J) agrees with recs and the API."""
from __future__ import annotations

import csv
from datetime import datetime

import pytest

from tests.contract import schemas


@pytest.fixture(scope="module")
def snaps(root):
    p = root / "data/synthetic_live/demo_night_snapshots.csv"
    if not p.exists():
        pytest.skip("demo_night_snapshots.csv not merged")
    with p.open(newline="") as f:
        return list(csv.DictReader(f))


def test_snapshot_shape(snaps, launch_ids):
    assert schemas.SNAPSHOT_COLUMNS <= set(snaps[0])
    ts = sorted({r["snapshot_ts"] for r in snaps})
    assert len(ts) == 15, ts  # 20:00 .. 03:00 every 30 min
    assert datetime.fromisoformat(ts[0]).strftime("%Y-%m-%d %H:%M") == "2026-11-14 20:00"
    assert datetime.fromisoformat(ts[-1]).strftime("%Y-%m-%d %H:%M") == "2026-11-15 03:00"
    assert {r["venue_id"] for r in snaps} == launch_ids
    assert all(r["is_synthetic"] == "1" for r in snaps)


def _f(x):
    return None if x in ("", None, "None", "nan") else float(x)


def test_snapshots_match_api(api, snaps):
    if api.get("/api/health").json().get("recs") != "real":
        pytest.xfail("backend on stub engine; snapshots are recs output (regenerated after ml-recs merge)")
    sample = [r for r in snaps if r["snapshot_ts"].startswith("2026-11-14T23:30") or r["snapshot_ts"].startswith("2026-11-14T21:00")]
    assert sample
    for r in sample:
        st = api.get(f"/api/venues/{r['venue_id']}/state", params={"now": r["snapshot_ts"]}).json()
        v, c = _f(r["vibe_score"]), _f(r["confidence"])
        if v is None:
            assert st["vibe_score"] is None, r
        else:
            assert st["vibe_score"] is not None and abs(st["vibe_score"] - v) <= 1 + 1e-9, (r, st)
        if c is not None:
            assert abs((st["confidence"] or 0) - c) <= 0.01 + 1e-9, (r, st)
