"""Extract the real public inputs for the 35 launch venues (run once; needs data/manhattan_bars.db).

Output: simulator/data/venue_inputs.csv (real public data, is_synthetic=0). The build
itself never touches manhattan_bars.db, so it runs on machines without the 39 MB DB.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
INPUTS = Path(__file__).resolve().parent / "data" / "venue_inputs.csv"
COLUMNS = ["license_id", "name", "lat", "lon", "osm_amenity", "osm_closes_late", "liquor_tier",
           "cuisine", "noise_complaints", "density_100m", "opening_hours", "is_synthetic"]


def extract(db_path: Path = ROOT / "data" / "manhattan_bars.db",
            launch_csv: Path = ROOT / "data" / "launch_venues.csv",
            out: Path = INPUTS) -> pd.DataFrame:
    """Join launch venues with venue_features and OSM opening hours; write the CSV."""
    lv = pd.read_csv(launch_csv, dtype={"license_id": str})
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)  # read-only
    try:
        feat = pd.read_sql("SELECT license_id, osm_amenity, osm_closes_late, liquor_tier, cuisine, "
                           "density_100m FROM venue_features", con)
        osm = pd.read_sql("SELECT osm_id, opening_hours FROM osm_venues", con)
    finally:
        con.close()
    df = lv.merge(feat, on="license_id", how="left").merge(osm, on="osm_id", how="left")
    df["is_synthetic"] = 0
    df = df[COLUMNS].sort_values("license_id").reset_index(drop=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, lineterminator="\n")
    return df


def load_inputs(path: Path = INPUTS) -> pd.DataFrame:
    """Read the committed venue inputs (venue_id = license_id)."""
    df = pd.read_csv(path, dtype={"license_id": str, "opening_hours": str}, keep_default_na=True)
    return df.rename(columns={"license_id": "venue_id"})
