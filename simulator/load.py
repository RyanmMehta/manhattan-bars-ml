"""Load syn_ CSV tables into data/live_sim.db (or $LIVE_SIM_DB). Never touches manhattan_bars.db."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pandas as pd

NAME_RE = re.compile(r"^syn_[a-z_]+$")
INDEXES = {"syn_scout_reports": [["venue_id", "ts"], ["scout_id", "ts"]], "syn_venue_updates": [["venue_id", "ts"]],
           "syn_venue_events": [["venue_id", "ts"]], "syn_true_state": [["venue_id", "ts"]],
           "syn_bounties": [["venue_id", "created_at"]], "syn_points_ledger": [["scout_id", "ts"]],
           "syn_scout_reputation_history": [["scout_id", "as_of_date"]]}


def check_target(db_path: Path) -> None:
    if Path(db_path).name == "manhattan_bars.db":
        raise ValueError("refusing to load synthetic tables into manhattan_bars.db (CONTRACTS v2 §D)")


def load(tables: dict[str, pd.DataFrame], db_path: Path) -> dict[str, int]:
    """Replace each syn_ table in db_path; returns row counts read back from the DB."""
    db_path = Path(db_path)
    check_target(db_path)
    bad = [n for n in tables if not NAME_RE.match(n)]
    if bad:
        raise ValueError(f"refusing non-syn_ table names: {bad}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    try:
        counts = {}
        for name, df in tables.items():
            con.execute(f'DROP TABLE IF EXISTS "{name}"')
            df.to_sql(name, con, index=False)
            for cols in INDEXES.get(name, []):
                con.execute(f'CREATE INDEX "ix_{name}_{"_".join(cols)}" ON "{name}" ({", ".join(cols)})')
            counts[name] = con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            if counts[name] != len(df):
                raise RuntimeError(f"{name}: row count mismatch {counts[name]} != {len(df)}")
        con.commit()
    finally:
        con.close()
    return counts
