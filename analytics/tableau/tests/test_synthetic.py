import math
from datetime import timedelta

import pandas as pd

import export_extracts as ex
import style


def test_synthetic_files_marked(exported):
    files = list((exported / "synthetic").glob("*.csv"))
    assert {f.name for f in files} == {"syn_tonight_heatmap.csv", "syn_tonight_reports.csv"}
    for f in files:
        assert f.name.startswith("syn_")
        df = pd.read_csv(f)
        assert len(df) > 0 and (df["is_synthetic"] == 1).all(), f.name


def test_heatmap_shape_and_ranges(exported):
    h = pd.read_csv(exported / "synthetic" / "syn_tonight_heatmap.csv")
    assert list(h.columns) == ex.HEATMAP_COLS
    assert len(h) == 35 * 7
    assert sorted(h["hour"].unique()) == [0, 1, 2, 20, 21, 22, 23]
    assert h["snapshot_ts"].str.contains(":30:00").all()  # HH:30 rule
    v = h["vibe_score"].dropna()
    assert v.between(0, 100).all()
    assert h["confidence"].dropna().between(0, 1).all()
    assert h["crowd"].dropna().between(1, 5).all()
    assert h["dancing"].dropna().between(0, 2).all()
    assert (h["line_minutes"].dropna() >= 0).all()
    # display rule (v2 §A)
    for _, r in h.iterrows():
        vib = None if pd.isna(r.vibe_score) else r.vibe_score
        conf = None if pd.isna(r.confidence) else r.confidence
        assert r.display == style.display_for(conf, vib)
    # DEMO_NOW column: 23:30 is not after now, 00:30 is
    assert (h.loc[h.hour == 23, "is_after_demo_now"] == 0).all()
    assert (h.loc[h.hour == 0, "is_after_demo_now"] == 1).all()
    assert set(h["source"]) == {"placeholder"}


def test_reports_ranges(exported):
    r = pd.read_csv(exported / "synthetic" / "syn_tonight_reports.csv")
    assert list(r.columns) == ex.REPORT_COLS
    assert r["crowd"].between(1, 5).all()
    assert r["dancing"].isin([0, 1, 2]).all()
    assert (r["line_minutes"] >= 0).all()
    assert r["report_id"].str.startswith("syn-r-T1-").all()
    assert r["scout_id"].str.startswith("syn-s-T1-").all()
    assert r["status"].isin(["accepted", "pending"]).all()


def test_golden_vector_g1():
    """specs PRD §5.8: vibe 65 / conf 0.67 (±1, ±0.01)."""
    now = ex.DEMO_NOW
    reps = pd.DataFrame({
        "scout_id": ["a", "b", "c", "d"],
        "ts": [now - timedelta(minutes=m) for m in (5, 12, 20, 40)],
        "crowd": [4, 4, 3, 4], "dancing": [2, 1, 1, 2], "line_minutes": [10, 15, 10, 5],
        "verified_presence": [1] * 4, "status": ["accepted"] * 4, "reputation": [0.8] * 4,
    })
    s = ex.fallback_state(reps, now)
    assert abs(s["vibe_score"] - 65) <= 1
    assert math.isclose(s["confidence"], 0.67, abs_tol=0.01)
    assert s["crowd"] == 3.8 and s["dancing"] == 1.5 and s["line_minutes"] == 10


def test_cutoff_and_empty():
    now = ex.DEMO_NOW
    reps = pd.DataFrame({"scout_id": ["a"], "ts": [now - timedelta(minutes=200)], "crowd": [5],
                         "dancing": [2], "line_minutes": [30], "verified_presence": [1],
                         "status": ["accepted"], "reputation": [0.5]})
    s = ex.fallback_state(reps, now)
    assert s["vibe_score"] is None and s["confidence"] is None and s["n_reports"] == 0


def test_snapshot_reader(tmp_path, exported):
    """A live-sim-shaped snapshot file (every 30 min) maps HH:30 rows into the heatmap."""
    h = pd.read_csv(exported / "synthetic" / "syn_tonight_heatmap.csv")
    snap = h[["venue_id", "snapshot_ts", "crowd", "dancing", "line_minutes", "vibe_score",
              "confidence", "n_reports", "is_synthetic"]].copy()
    # add HH:00 rows that must be ignored
    extra = snap.copy()
    extra["snapshot_ts"] = extra["snapshot_ts"].str.replace(":30:00", ":00:00")
    extra["vibe_score"] = 99
    p = tmp_path / "demo_night_snapshots.csv"
    pd.concat([snap, extra]).to_csv(p, index=False)
    assert list(pd.read_csv(p).columns) == ex.SNAPSHOT_COLS
    launch = pd.read_csv(exported / "launch_venues.csv")
    out = ex.heatmap_from_snapshots(p, launch)
    assert len(out) == 245 and set(out["source"]) == {"live-sim"}
    assert (out["vibe_score"].dropna() != 99).all()
    assert (out["is_synthetic"] == 1).all()
