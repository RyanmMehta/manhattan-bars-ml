"""Build output: schema, integrity, determinism, stage isolation, loader safety, replay, snapshots, rules."""
from __future__ import annotations

import hashlib
import sqlite3
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from simulator import config, load, replay, schema, snapshots, timeutil, trust, validate
from simulator.tests.conftest import run_build

REPO = Path(__file__).resolve().parents[2]


def _hashes(d: Path) -> dict:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.glob("*.csv"))}


def test_schema_every_table(small):
    for name, df in small["tables"].items():
        assert schema.check(df, name) == [], name
    assert len(small["tables"]) == 13


def test_no_hard_validation_failures(small):
    assert small["hard_fail"] == []
    v = small["validation"]
    for c in v["checks"]:
        if c["check"].startswith(("schema:", "fk:")):
            assert c["ok"], c


def test_ids_and_synthetic_flags(small):
    t = small["tables"]
    assert t["syn_scouts"]["scout_id"].str.match(r"^syn-s-\d{4}$").all()
    assert t["syn_scout_reports"]["report_id"].str.match(r"^syn-r-\d{6}$").all()
    assert t["syn_disputes"]["opened_by"].str.startswith("syn-o-").all()
    assert all((df["is_synthetic"] == 1).all() for df in t.values())


def test_prefs_json_matches_contract(small):
    import json
    keys = {"genres", "want_dancing", "crowd_pref", "max_cover_usd", "max_line_minutes", "max_distance_km", "lat",
            "lon", "group_size"}
    for p in small["tables"]["syn_users"]["prefs_json"]:
        d = json.loads(p)
        assert set(d) == keys and set(d["genres"]) <= set(config.GENRES)


def test_timestamps_local_iso(small):
    ts = small["tables"]["syn_scout_reports"]["ts"]
    assert ts.str.match(r"^2026-\d\d-\d\dT\d\d:\d\d:\d\d-0[45]:00$").all()
    h = pd.Series(timeutil.local_hour(pd.to_datetime(ts, utc=True, format="ISO8601")))
    assert ((h >= 20) & (h < 27)).all()


def test_determinism_and_seed(small, tmp_path):
    again = run_build(tmp_path / "b")
    assert _hashes(again["dir"]) == _hashes(small["dir"])
    other = run_build(tmp_path / "c", seed=7)
    assert _hashes(other["dir"])["syn_scout_reports.csv"] != _hashes(small["dir"])["syn_scout_reports.csv"]


def test_stage_isolation(tmp_path):
    import simulator
    a = simulator.generate(config.load("small", seed=42, nights=1))
    b = simulator.generate(config.load("small", seed=42, nights=1, users={"n": 25}))
    pd.testing.assert_frame_equal(a["syn_scout_reports"], b["syn_scout_reports"])
    assert len(b["syn_users"]) == 25


def test_reports_rules(small):
    t = small["tables"]
    r = t["syn_scout_reports"].copy()
    r["t"] = pd.to_datetime(r["ts"], utc=True, format="ISO8601")
    d = r["distance_m"]
    assert ((d.notna() & (d <= 150)).astype(int) == r["verified_presence"]).all()
    gap = r.sort_values("t").groupby(["scout_id", "venue_id"])["t"].diff().dropna()
    assert (gap >= pd.Timedelta(minutes=20)).all()
    per_hour = r.set_index("t").sort_index().groupby("scout_id")["report_id"].rolling("60min").count()
    assert per_hour.max() <= 6
    assert set(r["status"]) <= {"accepted", "flagged", "disputed", "removed"}


def test_no_reports_after_churn(small):
    t = small["tables"]
    last = pd.to_datetime(t["syn_scout_reports"]["ts"], utc=True, format="ISO8601").groupby(
        t["syn_scout_reports"]["scout_id"]).max()
    ch = pd.to_datetime(t["syn_scout_truth"].set_index("scout_id")["churned_at"], utc=True, format="ISO8601").dropna()
    assert not (last.reindex(ch.index) > ch).any()


def test_points_ledger_and_levels(small):
    t = small["tables"]
    s = t["syn_scouts"].set_index("scout_id")
    led = t["syn_points_ledger"].groupby("scout_id")["points"].sum()
    assert (s["points"] == led.reindex(s.index).fillna(0)).all()
    lv = config.load()["specs"]["levels"]
    assert all(trust.level_for(p, lv) == l for p, l in zip(s["points"], s["level"]))
    assert trust.level_for(99, lv) == "Rookie" and trust.level_for(100, lv) == "Regular"
    assert trust.level_for(1500, lv) == "Legend"


def test_closed_means_empty(small):
    import simulator
    t = simulator.generate(config.load("small", seed=42, nights=1))
    tr = t["syn_true_state"]
    closed = tr[~tr["_open"]]
    assert (closed["occupancy"] == 0).all() and (closed["crowd_true"] == 1).all()


def test_bounty_rules(small):
    b = small["tables"]["syn_bounties"].copy()
    for c in ("created_at", "expires_at", "claimed_at"):
        b[c] = pd.to_datetime(b[c], utc=True, format="ISO8601")
    assert ((b["expires_at"] - b["created_at"]) == pd.Timedelta(minutes=60)).all()
    cl = b.dropna(subset=["claimed_at"])
    assert ((cl["claimed_at"] >= cl["created_at"]) & (cl["claimed_at"] < cl["expires_at"])).all()
    assert b["points"].between(20, 50).all()
    h = pd.Series(timeutil.local_hour(b["created_at"]))
    assert ((h >= 21) & (h <= 26)).all()


def test_velocity_and_outlier_flags():
    sp = config.load()["specs"]
    v = pd.DataFrame({"venue_id": ["a", "b"], "lat": [40.72, 40.73], "lon": [-73.99, -73.99]})  # ~1.1 km apart
    t0 = pd.Timestamp("2026-11-14T23:00:00Z")
    rep = pd.DataFrame({"scout_id": ["s", "s", "u", "u"], "venue_id": ["a", "b", "a", "b"],
                        "ts": [t0, t0 + pd.Timedelta(minutes=2), t0, t0 + pd.Timedelta(minutes=30)]})
    assert list(trust.flag_velocity(rep, v, sp["velocity_kmh"])) == [False, True, False, False]
    rep2 = pd.DataFrame({"scout_id": ["x", "y", "z", "w"], "venue_id": ["a"] * 4,
                         "ts": [t0 + pd.Timedelta(minutes=m) for m in (0, 5, 10, 15)], "crowd": [5, 2, 2, 2]})
    out = trust.flag_outliers(rep2, pd.Series([True] * 4).to_numpy(), sp)
    assert list(out) == [True, False, False, False]


def test_loader_safety(small, tmp_path):
    with pytest.raises(ValueError):
        load.load({"venues": pd.DataFrame({"a": [1]})}, tmp_path / "x.db")
    with pytest.raises(ValueError):
        load.load({"syn_x": pd.DataFrame({"a": [1]})}, tmp_path / "manhattan_bars.db")
    db = tmp_path / "copy.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE venues (id INTEGER)")
    con.execute("INSERT INTO venues VALUES (1), (2)")
    con.commit()
    before = con.execute("SELECT group_concat(id) FROM venues").fetchone()
    con.close()
    load.load({"syn_x": pd.DataFrame({"a": [1, 2, 3]})}, db)
    con = sqlite3.connect(db)
    assert con.execute("SELECT group_concat(id) FROM venues").fetchone() == before
    assert con.execute("SELECT COUNT(*) FROM syn_x").fetchone()[0] == 3
    con.close()


def test_db_tables_and_counts(small):
    con = sqlite3.connect(small["db"])
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert names == set(schema.TABLES)
    for n, df in small["tables"].items():
        assert con.execute(f"SELECT COUNT(*) FROM {n}").fetchone()[0] == len(df)
    con.close()


def test_replay_visibility(small):
    now = "2026-11-14T23:30:00-05:00"
    seen = replay.visible(small["tables"], now)
    n = timeutil.parse_ts(now)
    assert (seen["syn_scout_reports"]["ts"] <= n + pd.Timedelta(minutes=2)).all()
    r = seen["syn_scout_reports"]
    young = (n - r["ts"]) < pd.Timedelta(minutes=30)
    assert (r.loc[r["status"] == "pending", "ts"] > n - pd.Timedelta(minutes=30)).all()
    assert not (young & (r["status"] == "accepted")).any()
    ob = seen["open_bounties"]
    assert (ob["expires_at"] > n).all() and ob["claimed_at"].isna().all()
    u = seen["syn_venue_updates"]
    assert not (u["offer_expires_at"].notna() & (u["offer_expires_at"] <= n)).any()
    assert "syn_true_state" not in seen and "syn_scout_truth" not in seen


def test_shift_keeps_time_of_night(small):
    from datetime import date
    sh = replay.shift(small["tables"], date(2026, 11, 17))
    r = sh["syn_scout_reports"]
    assert len(r) and (r["ts"].map(timeutil.night_of) == date(2026, 11, 17)).all()


def test_snapshots_file(small):
    s = pd.read_csv(small["dir"] / "demo_night_snapshots.csv")
    assert list(s.columns) == schema.SNAPSHOT_COLUMNS and len(s) == 525
    assert s["snapshot_ts"].nunique() == 15 and s["venue_id"].nunique() == 35
    assert s["snapshot_ts"].iloc[0] == "2026-11-14T20:00:00-05:00"
    assert s["snapshot_ts"].iloc[-1] == "2026-11-15T03:00:00-05:00"
    assert (s.loc[s["n_reports"] == 0, "vibe_score"].isna()).all()  # nulls stay null
    assert small["manifest"]["snapshot_source"] in ("recs", "fallback")


def test_validate_detects_broken_table(small):
    t = dict(small["tables"])
    t["syn_scout_reports"] = t["syn_scout_reports"].assign(is_synthetic=0)
    rep = validate.run(t, config.load("small", nights=3))
    assert not rep["ok"] and "all_rows_is_synthetic" in rep["failed"]


def test_cli_quick_mode(tmp_path):
    d = tmp_path / "synthetic_cli"
    p = subprocess.run([sys.executable, "-I", str(REPO / "simulator"), "--seed", "42", "--out",
                        str(d / "live_sim.db"), "--nights", "1", "--preset", "small", "--csv-dir", str(d)],
                       capture_output=True, text=True, cwd=REPO, timeout=60)
    assert p.returncode == 0, p.stderr[-2000:]
    assert (d / "live_sim.db").exists() and (d / "manifest.json").exists()


def test_refuses_plain_csv_dir(tmp_path):
    from simulator import build
    with pytest.raises(ValueError):
        build.build(out=str(tmp_path / "x.db"), nights=1, preset="small", csv_dir=str(tmp_path / "plain"))
