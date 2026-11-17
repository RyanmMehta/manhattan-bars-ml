"""Export the Tableau CSV extracts (E1-E7) from data/manhattan_bars.db (+ live-sim outputs).

    python -I analytics/tableau/export_extracts.py [--db ...] [--out ...] [--synthetic-dir ...]
                                                   [--snapshots ...] [--live-sim-db ...] [--placeholder]

Tonight-heatmap source precedence (OUTLINE §5):
  1. data/synthetic_live/demo_night_snapshots.csv (live-sim, v2.2 §J), HH:30 rows
  2. data/live_sim.db syn_scout_reports (env LIVE_SIM_DB) -> recs.live_state if importable, else local v2 scorer
  3. SYN-T1 placeholder reports (seed 42) -> same scorer
"""
from __future__ import annotations

import argparse
import math
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
import queries  # noqa: E402
import style  # noqa: E402

ET = ZoneInfo("America/New_York")
DEMO_NOW = datetime(2026, 11, 14, 23, 30, tzinfo=ET)  # CONTRACTS v2 §B
NIGHT_DATE = "2026-11-14"
NIGHT_START = datetime(2026, 11, 14, 20, 0, tzinfo=ET)
NIGHT_END = datetime(2026, 11, 15, 3, 0, tzinfo=ET)
HOURS = [20, 21, 22, 23, 0, 1, 2]  # cell HH = HH:30 snapshot; no 03 column
SEED = 42
PLACEHOLDER_RATE = 4.0  # reports/hour at peak; OUTLINE said 2, raised so the demo grid is readable (see workstream doc)

# v2 §A constants
HALF_LIFE_MIN = 30.0
CUTOFF_MIN = 180.0
FUTURE_TOL_MIN = 2.0
UNVERIFIED_W = 0.6
CONF_K = 1.5
MIN_FIELD_W = 0.30
VIBE_WEIGHTS = {"crowd": 0.50, "dance": 0.35, "line": 0.15}

REPORT_COLS = ["report_id", "venue_id", "scout_id", "ts", "crowd", "dancing", "line_minutes",
               "cover_usd", "music_genre", "verified_presence", "status", "distance_m", "is_synthetic"]
SNAPSHOT_COLS = ["venue_id", "snapshot_ts", "crowd", "dancing", "line_minutes", "vibe_score",
                 "confidence", "n_reports", "is_synthetic"]
HEATMAP_COLS = ["venue_id", "name", "lat", "lon", "night_date", "hour", "snapshot_ts", "hour_order",
                "hour_label", "vibe_score", "confidence", "display", "vibe_band", "n_reports", "crowd",
                "dancing", "line_minutes", "is_after_demo_now", "source", "is_synthetic"]


# ---------------------------------------------------------------- helpers
def connect_ro(path: Path) -> sqlite3.Connection:
    """Open a SQLite DB read-only."""
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """Deterministic CSV: UTF-8, '\\n' line endings, empty for missing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, lineterminator="\n", encoding="utf-8")


def round_cols(df: pd.DataFrame, coords=("lat", "lon"), scores=()) -> pd.DataFrame:
    for c in coords:
        if c in df:
            df[c] = df[c].round(5)
    for c in scores:
        if c in df:
            df[c] = df[c].astype(float).round(2)
    return df


def clean_grade(g):
    """NULL / 'None' (no DOHMH match) -> 'Not matched'."""
    return "Not matched" if g is None or g != g or g in ("None", "") else g


def hour_label(h: int) -> str:
    return f"{h % 12 or 12}{'pm' if 12 <= h < 24 else 'am'}"


# ---------------------------------------------------------------- public extracts
def build_bars(con, launch_ids: set) -> pd.DataFrame:
    """E1 bars.csv."""
    df = pd.read_sql_query(queries.BARS, con)
    df["has_coords"] = (df["lat"].notna() & df["lon"].notna()).astype(int)
    df["latest_grade"] = df["latest_grade"].map(clean_grade)
    df["complaint_bucket"] = df["noise_complaints"].map(style.complaint_bucket)
    df["is_launch"] = df["venue_id"].isin(launch_ids).astype(int)
    df["is_synthetic"] = 0
    for c in ("high_noise", "osm_closes_late"):
        df[c] = df[c].astype("Int64")
    df = round_cols(df, scores=("density_100m", "density_250m", "years_licensed"))
    cols = ["venue_id", "name", "address", "zip", "neighborhood", "lat", "lon", "has_coords",
            "venue_type", "liquor_tier", "latest_grade", "noise_complaints", "complaint_bucket",
            "high_noise", "density_100m", "density_250m", "years_licensed", "osm_amenity",
            "osm_closes_late", "is_launch", "is_synthetic"]
    return df[cols]


def build_features_slim(con) -> pd.DataFrame:
    """E2 venue_features_slim.csv."""
    df = pd.read_sql_query(queries.VENUE_FEATURES_SLIM, con)
    df["latest_grade"] = df["latest_grade"].map(clean_grade)
    df["is_synthetic"] = 0
    return round_cols(df, scores=("density_100m", "mean_score"))


def build_launch(launch_csv: Path, bars: pd.DataFrame) -> pd.DataFrame:
    """E3 launch_venues.csv (license_id aliased to venue_id; launch_rank = file order)."""
    lv = pd.read_csv(launch_csv, dtype={"zip": str}).rename(columns={"license_id": "venue_id"})
    lv["launch_rank"] = range(1, len(lv) + 1)
    lv = lv.merge(bars[["venue_id", "latest_grade"]], on="venue_id", how="left")
    lv["is_synthetic"] = 0
    lv = round_cols(lv)
    cols = ["venue_id", "name", "address", "lat", "lon", "venue_type", "latest_grade",
            "noise_complaints", "osm_id", "launch_rank", "is_synthetic"]
    return lv[cols].sort_values("venue_id").reset_index(drop=True)


def build_neighborhoods(con, bars: pd.DataFrame) -> pd.DataFrame:
    """E4 neighborhood_summary.csv (one row per neighbourhood in `venues`)."""
    counts = pd.read_sql_query(queries.VENUE_COUNTS, con)
    g = bars.groupby("neighborhood")
    agg = pd.DataFrame({
        "n_bars": g.size(),
        "n_clubs": g["venue_type"].apply(lambda s: int((s == "Club").sum())),
        "mean_density_100m": g["density_100m"].mean(),
        "total_complaints": g["noise_complaints"].sum(),
        "pct_high_noise": g["high_noise"].apply(lambda s: s.astype(float).mean() * 100),
        "pct_grade_a": g["latest_grade"].apply(lambda s: (s == "A").mean() * 100),
        "centroid_lat": g["lat"].mean(),
        "centroid_lon": g["lon"].mean(),
    }).reset_index()
    df = counts.merge(agg, on="neighborhood", how="left")
    df["n_bars"] = df["n_bars"].fillna(0).astype(int)
    df["n_clubs"] = df["n_clubs"].fillna(0).astype(int)
    df["total_complaints"] = df["total_complaints"].fillna(0).astype(int)
    df["complaints_per_bar"] = (df["total_complaints"] / df["n_bars"].replace(0, np.nan))
    df["is_synthetic"] = 0
    df = round_cols(df, coords=("centroid_lat", "centroid_lon"),
                    scores=("mean_density_100m", "complaints_per_bar", "pct_high_noise", "pct_grade_a"))
    cols = ["neighborhood", "n_venues", "n_bars", "n_clubs", "mean_density_100m", "total_complaints",
            "complaints_per_bar", "pct_high_noise", "pct_grade_a", "centroid_lat", "centroid_lon",
            "is_synthetic"]
    return df[cols].sort_values("neighborhood").reset_index(drop=True)


def build_grades(bars: pd.DataFrame) -> pd.DataFrame:
    """E5 grade_by_neighborhood.csv (every neighbourhood x grade, zeros kept)."""
    hoods = sorted(bars["neighborhood"].dropna().unique())
    idx = pd.MultiIndex.from_product([hoods, style.GRADE_ORDER], names=["neighborhood", "latest_grade"])
    n = bars.groupby(["neighborhood", "latest_grade"]).size().reindex(idx, fill_value=0)
    df = n.rename("n").reset_index()
    tot = df.groupby("neighborhood")["n"].transform("sum")
    df["pct"] = (df["n"] / tot * 100).round(2)
    df["grade_order"] = df["latest_grade"].map({g: i for i, g in enumerate(style.GRADE_ORDER)})
    df["is_synthetic"] = 0
    return df[["neighborhood", "latest_grade", "grade_order", "n", "pct", "is_synthetic"]]


# ---------------------------------------------------------------- synthetic: reports
def make_placeholder_reports(launch: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    """SYN-T1: placeholder scout reports at the 35 launch venues, Sat Nov 14 20:00-03:00 ET."""
    # SYNTHETIC: live-sim data/live_sim.db syn_scout_reports, then real scout_reports (backend)
    rng = np.random.default_rng(seed)
    n_scouts = 60
    rows = []
    venues = sorted(launch["venue_id"])
    dancers = set(rng.choice(venues, size=max(1, round(0.2 * len(venues))), replace=False))
    night_hours = list(range(20, 27))  # 20..26 (26 = 02:00 next day)
    for vid in venues:
        peak = int(rng.choice([22, 23, 24, 25]))
        size = rng.uniform(0.6, 1.4)  # venue popularity
        for h in night_hours:
            curve = math.exp(-0.5 * ((h + 0.5 - peak) / 1.5) ** 2)
            k = rng.poisson(PLACEHOLDER_RATE * curve * size)
            for _ in range(k):
                minute = int(rng.integers(0, 60))
                ts = NIGHT_START + timedelta(hours=h - 20, minutes=minute)
                crowd = int(np.clip(round(rng.normal(1 + 4 * curve * min(size, 1.0), 0.7)), 1, 5))
                if crowd >= 4 and vid in dancers:
                    dancing = int(rng.choice([1, 2], p=[0.6, 0.4]))
                else:
                    dancing = 0
                line = int(round(rng.gamma(2.0, 4.0))) if crowd >= 4 else 0
                rows.append({
                    "venue_id": vid,
                    "scout_id": f"syn-s-T1-{int(rng.integers(1, n_scouts + 1)):04d}",
                    "ts": ts,
                    "crowd": crowd, "dancing": dancing, "line_minutes": line,
                    "cover_usd": None, "music_genre": None,
                    "verified_presence": int(rng.random() < 0.8),
                    "status": "accepted", "distance_m": None, "is_synthetic": 1,
                })
    df = pd.DataFrame(rows).sort_values(["ts", "venue_id", "scout_id"]).reset_index(drop=True)
    df.insert(0, "report_id", [f"syn-r-T1-{i:06d}" for i in range(1, len(df) + 1)])
    df["reputation"] = 0.5  # new-scout default (v2 §A); placeholder has no history
    return df


def load_live_sim_reports(db: Path, launch_ids: set) -> pd.DataFrame:
    """Live-sim syn_scout_reports for the demo night (accepted + pending, reputation as of report date)."""
    # SYNTHETIC: live-sim data/live_sim.db; real source = backend scout_reports (INCLUDE_SYNTHETIC=0)
    with connect_ro(db) as con:
        df = pd.read_sql_query(queries.LIVE_SIM_REPORTS, con,
                               params={"start": "2026-11-14T12", "end": "2026-11-15T12"})
    df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert(ET)
    df = df[(df["ts"] >= NIGHT_START - timedelta(minutes=CUTOFF_MIN)) & (df["ts"] < NIGHT_END)]
    return df[df["venue_id"].isin(launch_ids)].reset_index(drop=True)


# ---------------------------------------------------------------- scoring
def _wmedian(values, weights):
    order = np.argsort(values, kind="stable")
    v, w = np.asarray(values)[order], np.asarray(weights)[order]
    cum = np.cumsum(w)
    return float(v[np.searchsorted(cum, cum[-1] / 2.0)])


def fallback_state(reports: pd.DataFrame, now: datetime) -> dict:
    """Live Venue State per docs/prd/specs/PRD.md §5.2-5.6 (v2 §A constants).

    # SYNTHETIC: replace with recs.live_state (ml-recs) once merged.
    Passes golden vector G1 (vibe 65 / conf 0.67). `reports` needs ts, crowd, dancing,
    line_minutes, verified_presence, status, reputation, scout_id.
    """
    empty = {"crowd": None, "dancing": None, "line_minutes": None, "vibe_score": None,
             "confidence": None, "n_reports": 0}
    if reports.empty:
        return empty
    age = np.array([(now - t).total_seconds() / 60.0 for t in reports["ts"]])
    keep = (age <= CUTOFF_MIN) & (age >= -FUTURE_TOL_MIN)
    r = reports[keep].copy()
    if r.empty:
        return empty
    age = np.clip(age[keep], 0, None)
    rep = r["reputation"].fillna(0.5).to_numpy(float)
    ver = np.where(r["verified_presence"].to_numpy() == 1, 1.0, UNVERIFIED_W)
    stat = r["status"].map({"accepted": 1.0, "pending": 1.0, "disputed": 0.5}).fillna(0.0).to_numpy()
    w = 0.5 ** (age / HALF_LIFE_MIN) * (0.25 + 0.75 * rep) * ver * stat
    r["w"] = w
    r = r[r["w"] > 0]
    if r.empty:
        return empty

    def field(col):
        s = r[r[col].notna()]
        return s if s["w"].sum() >= MIN_FIELD_W else None

    c, d, ln = field("crowd"), field("dancing"), field("line_minutes")
    crowd = float(np.average(c["crowd"], weights=c["w"])) if c is not None else None
    dancing = float(np.average(d["dancing"], weights=d["w"])) if d is not None else None
    line = int(_wmedian(ln["line_minutes"].to_numpy(float), ln["w"].to_numpy())) if ln is not None else None

    vibe = conf = None
    if crowd is not None:
        terms = {"crowd": (crowd - 1) / 4}
        if dancing is not None:
            terms["dance"] = dancing / 2
        if line is not None:
            terms["line"] = min(line, 30) / 30
        a = sum(VIBE_WEIGHTS[k] for k in terms)
        vibe = int(round(100 * sum(VIBE_WEIGHTS[k] * x for k, x in terms.items()) / a))
        cw = r[r["crowd"].notna()]
        W = cw["w"].sum()
        support = 1 - math.exp(-W / CONF_K)
        mu = np.average(cw["crowd"], weights=cw["w"])
        sd = math.sqrt(np.average((cw["crowd"] - mu) ** 2, weights=cw["w"]))
        agree = 1 - 0.5 * min(1.0, sd / 1.5)
        diverse = 1.0 if cw["scout_id"].nunique() >= 2 else 0.6
        conf = round(support * agree * diverse, 2)
    return {"crowd": None if crowd is None else round(crowd, 1),
            "dancing": None if dancing is None else round(dancing, 1),
            "line_minutes": line, "vibe_score": vibe, "confidence": conf,
            "n_reports": int(len(r))}


def recs_states(reports: pd.DataFrame, now: datetime):
    """Try recs.live_state.compute_all (ml-recs); return None if recs is not importable."""
    try:
        from recs import live_state  # type: ignore
    except Exception:
        return None
    rep = reports.copy()
    rep["ts"] = rep["ts"].map(lambda t: t.isoformat())
    states = live_state.compute_all(rep, pd.DataFrame(columns=["update_id", "venue_id", "ts"]), now)
    return {s["venue_id"]: s for s in states}


def snapshot_times():
    """(hour, hour_order, snapshot datetime) for each heatmap column: HH:30 rule (v2.2 §J)."""
    out = []
    for i, h in enumerate(HOURS):
        day = 14 if h >= 20 else 15
        out.append((h, i, datetime(2026, 11, day, h, 30, tzinfo=ET)))
    return out


def heatmap_from_reports(reports: pd.DataFrame, launch: pd.DataFrame, source: str) -> pd.DataFrame:
    """E6 from report rows: state at each HH:30 snapshot per launch venue."""
    rows = []
    by_venue = {v: g for v, g in reports.groupby("venue_id")}
    for h, order, snap in snapshot_times():
        rstates = recs_states(reports, snap) if not reports.empty else None
        for vid in sorted(launch["venue_id"]):
            if rstates is not None:
                s = rstates.get(vid, {})
            else:
                s = fallback_state(by_venue.get(vid, reports.iloc[0:0]), snap)
            rows.append({"venue_id": vid, "hour": h, "hour_order": order, "snapshot_ts": snap,
                         **{k: s.get(k) for k in ("crowd", "dancing", "line_minutes", "vibe_score",
                                                   "confidence", "n_reports")}})
    return finish_heatmap(pd.DataFrame(rows), launch, source)


def heatmap_from_snapshots(path: Path, launch: pd.DataFrame) -> pd.DataFrame:
    """E6 from live-sim demo_night_snapshots.csv: keep HH:30 rows only."""
    # SYNTHETIC: live-sim data/synthetic_live/demo_night_snapshots.csv; real = GET /api/heatmap?by=hour
    snap = pd.read_csv(path)
    missing = set(SNAPSHOT_COLS) - set(snap.columns)
    if missing:
        raise ValueError(f"{path} missing columns {sorted(missing)}")
    snap["snapshot_ts"] = pd.to_datetime(snap["snapshot_ts"], utc=True).dt.tz_convert(ET)
    want = {s: (h, o) for h, o, s in snapshot_times()}
    snap = snap[snap["snapshot_ts"].isin(list(want))].copy()
    snap["hour"] = snap["snapshot_ts"].map(lambda t: want[t][0])
    snap["hour_order"] = snap["snapshot_ts"].map(lambda t: want[t][1])
    # every launch venue x hour present, even if live-sim omitted a row (stays null)
    grid = pd.DataFrame([(v, h, o, s) for h, o, s in snapshot_times() for v in sorted(launch["venue_id"])],
                        columns=["venue_id", "hour", "hour_order", "snapshot_ts"])
    df = grid.merge(snap.drop(columns=["snapshot_ts", "hour"]), on=["venue_id", "hour_order"], how="left")
    df["n_reports"] = df["n_reports"].fillna(0)
    return finish_heatmap(df, launch, "live-sim")


def finish_heatmap(df: pd.DataFrame, launch: pd.DataFrame, source: str) -> pd.DataFrame:
    """Add names/coords, display, band, labels; round; order columns."""
    df = df.merge(launch[["venue_id", "name", "lat", "lon"]], on="venue_id", how="left")
    df["night_date"] = NIGHT_DATE
    df["hour_label"] = df["hour"].map(hour_label)
    df["is_after_demo_now"] = (df["snapshot_ts"] > DEMO_NOW).astype(int)
    df["snapshot_ts"] = df["snapshot_ts"].map(lambda t: t.isoformat())
    df["vibe_score"] = pd.to_numeric(df["vibe_score"]).round().astype("Int64")
    df["confidence"] = pd.to_numeric(df["confidence"]).astype(float).round(2)
    df["crowd"] = pd.to_numeric(df["crowd"]).astype(float).round(1)
    df["dancing"] = pd.to_numeric(df["dancing"]).astype(float).round(1)
    df["line_minutes"] = pd.to_numeric(df["line_minutes"]).round().astype("Int64")
    df["n_reports"] = pd.to_numeric(df["n_reports"]).fillna(0).astype(int)
    df["display"] = [style.display_for(c, None if pd.isna(v) else v)
                     for c, v in zip(df["confidence"], df["vibe_score"])]
    df["vibe_band"] = [None if pd.isna(v) else style.vibe_band(v) for v in df["vibe_score"]]
    df["source"] = source
    df["is_synthetic"] = 1
    df = round_cols(df)
    return df[HEATMAP_COLS].sort_values(["hour_order", "venue_id"]).reset_index(drop=True)


def reports_for_csv(reports: pd.DataFrame) -> pd.DataFrame:
    """E7: v2 syn_scout_reports columns, ISO ts."""
    out = reports.copy()
    if out.empty:
        return pd.DataFrame(columns=REPORT_COLS)
    out["ts"] = out["ts"].map(lambda t: t.isoformat())
    for c in ("cover_usd", "distance_m"):
        out[c] = pd.to_numeric(out[c]).astype("Int64")
    out["is_synthetic"] = 1
    return out[REPORT_COLS].sort_values("report_id").reset_index(drop=True)


# ---------------------------------------------------------------- main
def export(db: Path, out: Path, synthetic_dir: Path, launch_csv: Path, snapshots: Path | None,
           live_sim_db: Path | None, placeholder: bool) -> dict:
    """Write every extract; return {name: rows} plus the tonight source used."""
    with connect_ro(db) as con:
        launch_ids = set(pd.read_csv(launch_csv)["license_id"])
        bars = build_bars(con, launch_ids)
        slim = build_features_slim(con)
        hoods = build_neighborhoods(con, bars)
    launch = build_launch(launch_csv, bars)
    grades = build_grades(bars)
    files = {
        out / "bars.csv": bars, out / "venue_features_slim.csv": slim,
        out / "launch_venues.csv": launch, out / "neighborhood_summary.csv": hoods,
        out / "grade_by_neighborhood.csv": grades,
    }

    # SYNTHETIC: tonight heatmap; real replacement = GET /api/heatmap?now=...&by=hour (backend)
    if not placeholder and snapshots is not None and snapshots.exists():
        heat = heatmap_from_snapshots(snapshots, launch)
        reports = (load_live_sim_reports(live_sim_db, launch_ids)
                   if live_sim_db is not None and live_sim_db.exists() else pd.DataFrame())
    elif not placeholder and live_sim_db is not None and live_sim_db.exists():
        reports = load_live_sim_reports(live_sim_db, launch_ids)
        heat = heatmap_from_reports(reports, launch, "live-sim")
    else:
        reports = make_placeholder_reports(launch)
        heat = heatmap_from_reports(reports, launch, "placeholder")
    files[synthetic_dir / "syn_tonight_heatmap.csv"] = heat
    files[synthetic_dir / "syn_tonight_reports.csv"] = reports_for_csv(reports)

    for path, df in files.items():
        write_csv(df, path)
    summary = {p.name: len(df) for p, df in files.items()}
    summary["tonight_source"] = heat["source"].iloc[0]
    return summary


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", type=Path, default=ROOT / "data" / "manhattan_bars.db")
    p.add_argument("--launch", type=Path, default=ROOT / "data" / "launch_venues.csv")
    p.add_argument("--out", type=Path, default=HERE / "extracts")
    p.add_argument("--synthetic-dir", type=Path, default=None,
                   help="default: <out>/synthetic")
    p.add_argument("--snapshots", type=Path,
                   default=ROOT / "data" / "synthetic_live" / "demo_night_snapshots.csv")
    p.add_argument("--live-sim-db", type=Path,
                   default=Path(os.environ.get("LIVE_SIM_DB", ROOT / "data" / "live_sim.db")))
    p.add_argument("--placeholder", action="store_true", help="force the SYN-T1 placeholder")
    a = p.parse_args(argv)
    if not a.db.exists():
        sys.exit(f"DB not found: {a.db}")
    summary = export(a.db, a.out, a.synthetic_dir or a.out / "synthetic", a.launch, a.snapshots,
                     a.live_sim_db, a.placeholder)
    for k, v in summary.items():
        print(f"{k:32s} {v}")


if __name__ == "__main__":
    main()
