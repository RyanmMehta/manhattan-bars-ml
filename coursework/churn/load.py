"""Load the Scout tables the churn model needs, from data/live_sim.db or the stand-in CSVs.

Inputs : data/live_sim.db (env LIVE_SIM_DB overrides the path), opened READ-ONLY, or
         coursework/churn/outputs/synthetic/standin_*.csv (fallback, see make_standin_data.py)
Outputs: dict of pandas DataFrames: scouts, reports, ledger, bounties, rep_history
Run    : python -I coursework/churn/load.py        (prints row counts and the source used)

This file NEVER loads the evaluation-only Scout table (RULES.md §3: only the evaluation script may).
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from coursework.common import LIVE_SIM_DB, connect_read_only  # noqa: E402

STANDIN_DIR = Path(__file__).resolve().parent / "outputs" / "synthetic"
NY = "America/New_York"

# Contract columns we rely on (CONTRACTS.md base schema + v2 §E additions).
TABLES = {
    "scouts": ("syn_scouts", ["scout_id", "joined_at", "is_synthetic"]),
    "reports": ("syn_scout_reports", ["report_id", "venue_id", "scout_id", "ts", "verified_presence",
                                      "status", "distance_m", "is_synthetic"]),
    "ledger": ("syn_points_ledger", ["entry_id", "scout_id", "bounty_id", "points", "ts", "is_synthetic"]),
    "bounties": ("syn_bounties", ["bounty_id", "claimed_by", "claimed_at", "is_synthetic"]),
    "rep_history": ("syn_scout_reputation_history", ["scout_id", "as_of_date", "reputation", "points",
                                                      "level", "is_synthetic"]),
}
TIME_COLUMNS = {"scouts": ["joined_at"], "reports": ["ts"], "ledger": ["ts"], "bounties": ["claimed_at"]}


def to_ny(series: pd.Series) -> pd.Series:
    """Parse ISO strings with mixed -04:00/-05:00 offsets (DST ends Nov 1) into New York time."""
    return pd.to_datetime(series, utc=True, format="ISO8601").dt.tz_convert(NY)


def pick_source() -> str:
    return "db" if LIVE_SIM_DB.exists() else "standin"


def load(source: str = "auto", directory: Path = STANDIN_DIR) -> dict:
    """Return the five tables as DataFrames, with times parsed and columns validated.

    directory: where standin_*.csv live (tests point it at tests/fixtures/synthetic/).
    """
    source = pick_source() if source == "auto" else source
    frames = {}
    for key, (table, needed) in TABLES.items():
        if source == "db":
            # SYNTHETIC: replace with the backend's real tables (same names without syn_)
            with connect_read_only(LIVE_SIM_DB) as conn:
                df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        else:
            # SYNTHETIC: stand-in CSVs; replace with live-sim's data/live_sim.db
            df = pd.read_csv(directory / f"standin_{table.removeprefix('syn_')}.csv")
        missing = [c for c in needed if c not in df.columns]
        if missing:
            raise ValueError(f"{table} is missing contract columns {missing}")
        for col in TIME_COLUMNS.get(key, []):
            df[col] = to_ny(df[col])
        frames[key] = df
    frames["source"] = source
    return frames


if __name__ == "__main__":
    data = load()
    print(f"source: {data.pop('source')}")
    for key, df in data.items():
        print(f"{key:12s} {len(df):7d} rows")
