"""Turn raw Scout activity into one row per Scout: features (before the cutoff) + churn label (after).

Inputs : tables from load.py (live_sim.db or stand-in CSVs)
Outputs: outputs/synthetic/churn_dataset_<cutoff>.csv for the train and test cutoffs (is_synthetic=1)
Run    : python -I coursework/churn/build_dataset.py
         python -I coursework/churn/build_dataset.py --cutoffs 2026-10-01 2026-10-22 --lookback-days 28 --horizon-days 21

Timeline (both cutoffs are Thursdays at 12:00 ET, so no Thu-Sat night is split)       [N2][N4]
  train: features use ts < Oct 1 (lookback Sep 3-30) | label window Oct 1 - Oct 21
  test : features use ts < Oct 22 (lookback Sep 24-Oct 21) | label window Oct 22 - Nov 11
Eligible  = joined before the cutoff AND >= 1 report in the 28 days before it.
Churned=1 = 0 reports in the 21 days from the cutoff (CONTRACTS v2.1 §B).
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from coursework.churn.load import NY, load  # noqa: E402

OUT = Path(__file__).resolve().parent / "outputs" / "synthetic"
TRAIN_CUTOFF, TEST_CUTOFF = "2026-10-01", "2026-10-22"
FIRST_DAY = pd.Timestamp("2026-08-27", tz=NY)  # first simulated night; cohort_week counts from here

# [N3] Feature list. End-of-sim snapshot columns of syn_scouts (reputation, points, level,
# reports_count, last_active_at) are deliberately NOT here: they contain the future. [N4]
FEATURES = ["tenure_days", "cohort_week", "reports_28d", "reports_7d", "days_since_last_report",
            "active_nights_28d", "mean_gap_days", "trend", "share_verified_presence",
            "share_flagged_or_removed", "median_distance_m", "distinct_venues_28d",
            "share_saturday_reports", "points_28d", "points_total", "bounties_claimed_28d",
            "reputation_asof", "points_asof", "level_asof"]


# live-sim stores level as a name; the order comes from its points bands (Rookie < 100 <= Regular
# < 500 <= Insider < 1500 <= Legend). Numbers (the stand-in) pass through unchanged.
LEVEL_ORDER = {"Rookie": 1, "Regular": 2, "Insider": 3, "Legend": 4}


def cutoff_ts(date: str) -> pd.Timestamp:
    return pd.Timestamp(f"{date} 12:00", tz=NY)


def night_of(ts: pd.Series) -> pd.Series:
    """A report at 01:30 Sunday belongs to Saturday night: shift back 6 h, take the date."""
    return (ts - pd.Timedelta(hours=6)).dt.normalize()


def activity_features(r: pd.DataFrame, cutoff: pd.Timestamp, lookback: int) -> dict:
    """[N3] Features from ONE Scout's reports, all with ts < cutoff (filtered by the caller)."""
    counted = r[r["status"] != "removed"]          # removed reports don't count as activity
    last_28 = counted[counted["ts"] >= cutoff - pd.Timedelta(days=lookback)]
    last_7 = counted[counted["ts"] >= cutoff - pd.Timedelta(days=7)]
    nights = np.sort(night_of(counted["ts"]).unique())
    gaps = np.diff(nights) / pd.Timedelta(days=1) if len(nights) > 1 else []
    prior_21_rate = (len(last_28) - len(last_7)) / 3   # reports per week in the 21 days before the last 7
    return {
        "reports_28d": len(last_28),
        "reports_7d": len(last_7),
        "days_since_last_report": (cutoff - counted["ts"].max()) / pd.Timedelta(days=1),
        "active_nights_28d": night_of(last_28["ts"]).nunique(),
        "mean_gap_days": float(np.mean(gaps)) if len(gaps) else np.nan,  # NaN = only 1 night so far
        "trend": len(last_7) - prior_21_rate,   # > 0 = more active lately, < 0 = slowing down
        "share_verified_presence": r["verified_presence"].mean(),
        "share_flagged_or_removed": r["status"].isin(["flagged", "removed"]).mean(),
        "median_distance_m": r["distance_m"].median(),   # NaN if never verified
        "distinct_venues_28d": last_28["venue_id"].nunique(),
        "share_saturday_reports": (night_of(counted["ts"]).dt.weekday == 5).mean(),
    }


def asof_reputation(history: pd.DataFrame, cutoff: pd.Timestamp) -> dict:
    """[N4] Latest reputation-history row with as_of_date < cutoff date (never the final value)."""
    before = history[pd.to_datetime(history["as_of_date"]) < pd.Timestamp(cutoff.date())]
    if before.empty:
        return {"reputation_asof": 0.5, "points_asof": 0, "level_asof": 1}  # contract default r = 0.5
    last = before.sort_values("as_of_date").iloc[-1]
    level = LEVEL_ORDER.get(last["level"], last["level"])  # name -> ordinal 1-4
    return {"reputation_asof": last["reputation"], "points_asof": last["points"], "level_asof": int(level)}


def build(data: dict, cutoff_date: str, lookback: int = 28, horizon: int = 21) -> pd.DataFrame:
    """One row per eligible Scout: id, cutoff, FEATURES, churned, is_synthetic."""
    cutoff = cutoff_ts(cutoff_date)
    reports, ledger = data["reports"], data["ledger"]
    past = reports[reports["ts"] < cutoff]                                   # [N4] features: before only
    future = reports[(reports["ts"] >= cutoff) & (reports["ts"] < cutoff + pd.Timedelta(days=horizon))
                     & (reports["status"] != "removed")]                     # label: after only
    claims = data["bounties"].dropna(subset=["claimed_at"])
    rows = []
    for _, scout in data["scouts"].iterrows():
        sid, joined = scout["scout_id"], scout["joined_at"]
        mine = past[past["scout_id"] == sid]
        recent = mine[(mine["ts"] >= cutoff - pd.Timedelta(days=lookback)) & (mine["status"] != "removed")]
        if joined >= cutoff or recent.empty:
            continue                                                         # [N2] not eligible
        pts = ledger[(ledger["scout_id"] == sid) & (ledger["ts"] < cutoff)]
        my_claims = claims[(claims["claimed_by"] == sid) & (claims["claimed_at"] < cutoff)]
        row = {"scout_id": sid, "cutoff": cutoff_date,
               "tenure_days": (cutoff - joined) / pd.Timedelta(days=1),
               "cohort_week": max(0, int((joined - FIRST_DAY).days // 7)),  # pre-launch sign-ups = week 0
               "points_28d": pts.loc[pts["ts"] >= cutoff - pd.Timedelta(days=lookback), "points"].sum(),
               "points_total": pts["points"].sum(),
               "bounties_claimed_28d": int((my_claims["claimed_at"] >= cutoff - pd.Timedelta(days=lookback)).sum())}
        row.update(activity_features(mine, cutoff, lookback))
        row.update(asof_reputation(data["rep_history"][data["rep_history"]["scout_id"] == sid], cutoff))
        row["churned"] = int((future["scout_id"] == sid).sum() == 0)        # [N2] 0 reports in 21 days
        row["is_synthetic"] = 1  # SYNTHETIC: built from synthetic Scouts; real reports replace it
        rows.append(row)
    return pd.DataFrame(rows, columns=["scout_id", "cutoff"] + FEATURES + ["churned", "is_synthetic"])


def check(df: pd.DataFrame, name: str) -> None:
    n, churners = len(df), int(df["churned"].sum())
    rate = churners / n if n else float("nan")
    print(f"{name}: {n} eligible Scouts, {churners} churned, base rate {rate:.1%}")
    if n < 60 or churners < 15 or not 0.05 <= rate <= 0.60:
        print(f"  WARNING: small or unbalanced snapshot (want >= 60 Scouts, >= 15 churners, 5-60%)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cutoffs", nargs=2, default=[TRAIN_CUTOFF, TEST_CUTOFF], metavar=("TRAIN", "TEST"))
    p.add_argument("--lookback-days", type=int, default=28)
    p.add_argument("--horizon-days", type=int, default=21)
    p.add_argument("--source", choices=["auto", "db", "standin"], default="auto")
    args = p.parse_args()
    data = load(args.source)
    print(f"source: {data['source']}")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, date in zip(["train", "test"], args.cutoffs):
        df = build(data, date, args.lookback_days, args.horizon_days)
        check(df, f"{name} snapshot (cutoff {date})")
        df.to_csv(OUT / f"churn_dataset_{date}.csv", index=False)  # SYNTHETIC: derived from syn_ tables


if __name__ == "__main__":
    main()
