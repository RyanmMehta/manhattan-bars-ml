"""Read-only loaders. Library code that scores/ranks never calls these; the CLI, models and reports do.

- Public data: data/manhattan_bars.db (venues, osm_venues, venue_features, v_bars), data/launch_venues.csv.
- Live data: data/live_sim.db from live-sim (syn_* tables) when present, else recs' own interim stub
  (recs/synthetic/stub_nights.py, same schemas).
All DB connections are opened read-only.
"""
from __future__ import annotations

import logging
import os
import sqlite3
from functools import lru_cache
from pathlib import Path

import pandas as pd

log = logging.getLogger("recs")

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
BARS_DB = DATA / "manhattan_bars.db"
LIVE_DB = Path(os.environ.get("LIVE_SIM_DB") or DATA / "live_sim.db")  # env name reserved in CONTRACTS §H
LAUNCH_CSV = DATA / "launch_venues.csv"
LAUNCH_FULL_CSV = DATA / "launch_venues_full.csv"
MANUAL_ATTRS = DATA / "venue_attributes_manual.csv"

LIVE_TABLES = {
    "syn_scout_reports": ["report_id", "venue_id", "scout_id", "ts", "crowd", "dancing", "line_minutes",
                          "cover_usd", "music_genre", "verified_presence", "is_synthetic"],
    "syn_scouts": ["scout_id", "reputation", "is_synthetic"],
    "syn_venue_updates": ["update_id", "venue_id", "ts", "cover_usd", "genres", "is_synthetic"],
    "syn_venue_attributes": ["venue_id", "genres", "style", "has_dance_floor", "typical_cover_usd", "capacity",
                             "price_level", "is_synthetic"],
}


def _ro(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def has_bars_db() -> bool:
    return BARS_DB.exists()


def has_live_db() -> bool:
    return LIVE_DB.exists()


@lru_cache(maxsize=1)
def launch_venues() -> pd.DataFrame:
    """35 launch venues: venue_id (= license_id), name, lat, lon, opening_hours, + public fields."""
    if LAUNCH_FULL_CSV.exists():
        df = pd.read_csv(LAUNCH_FULL_CSV)
    else:
        df = pd.read_csv(LAUNCH_CSV)
        if has_bars_db():
            with _ro(BARS_DB) as c:
                osm = pd.read_sql("SELECT osm_id, name AS osm_name, opening_hours FROM osm_venues", c)
            df = df.merge(osm, on="osm_id", how="left")
            df["display_name"] = df["osm_name"].fillna(df["name"].str.title())
            df = df.drop(columns=["osm_name"])
    df = df.rename(columns={"license_id": "venue_id"})
    if "opening_hours" not in df:
        df["opening_hours"] = None
    if "display_name" not in df:
        df["display_name"] = df["name"].str.title()
    return df


@lru_cache(maxsize=1)
def venue_features(bars_only: bool = True) -> pd.DataFrame:
    """Real public `venue_features` (optionally restricted to v_bars)."""
    with _ro(BARS_DB) as c:
        if bars_only:
            return pd.read_sql("SELECT f.* FROM venue_features f JOIN v_bars b ON b.license_id = f.license_id", c)
        return pd.read_sql("SELECT * FROM venue_features", c)


def _read_live(table: str) -> pd.DataFrame:
    with _ro(LIVE_DB) as c:
        df = pd.read_sql(f"SELECT * FROM {table}", c)  # noqa: S608 - fixed table names
    need = LIVE_TABLES.get(table, [])
    miss = [col for col in need if col not in df.columns]
    if miss:
        raise ValueError(f"{LIVE_DB}:{table} missing columns {miss} (schema drift vs CONTRACTS §E)")
    return df


@lru_cache(maxsize=4)
def live_tables(source: str = "auto") -> dict[str, pd.DataFrame]:
    """syn_* tables as DataFrames. source: 'auto' (live_sim.db if present, else stub) | 'live_sim' | 'stub'.

    # SYNTHETIC: live-sim's data/live_sim.db (then real app tables scout_reports, venue_updates, ...)
    """
    if source in ("auto", "live_sim") and has_live_db():
        names = ["syn_scout_reports", "syn_scouts", "syn_venue_updates", "syn_venue_attributes",
                 "syn_scout_reputation_history", "syn_true_state"]
        out = {}
        for n in names:
            try:
                out[n] = _read_live(n)
            except Exception as e:  # noqa: BLE001
                log.warning("live_sim.db: %s unavailable (%s)", n, e)
        out["_source"] = "live_sim"
        return _apply_manual(out)
    if source == "live_sim":
        raise FileNotFoundError(LIVE_DB)
    from .synthetic import stub_nights  # SYNTHETIC: interim stub until live-sim lands
    out = stub_nights.generate(launch_venues())
    out["_source"] = "stub"
    return _apply_manual(out)


def _apply_manual(t: dict) -> dict:
    """data/venue_attributes_manual.csv rows (is_synthetic=0) override synthetic attributes (CONTRACTS v2 §D)."""
    if MANUAL_ATTRS.exists() and "syn_venue_attributes" in t:
        man = pd.read_csv(MANUAL_ATTRS)
        a = t["syn_venue_attributes"]
        a = pd.concat([a[~a["venue_id"].isin(man["venue_id"])], man], ignore_index=True)
        t["syn_venue_attributes"] = a
    return t


def venues_for_scoring(source: str = "auto") -> list[dict]:
    """Launch venues + attributes in the shape scoring/routing expect."""
    v = launch_venues()
    attrs = live_tables(source).get("syn_venue_attributes")
    if attrs is not None:
        drop = [c for c in ("opening_hours",) if c in attrs.columns and v["opening_hours"].notna().any()]
        v = v.merge(attrs.drop(columns=drop).rename(columns={"is_synthetic": "attr_is_synthetic"}),
                    on="venue_id", how="left")
        v["is_synthetic"] = v["attr_is_synthetic"].fillna(0).astype(int)
    v = v.copy()
    v["name"] = v["display_name"]
    from .inputs import rows
    return rows(v)


def reports_with_reputation(source: str = "auto") -> pd.DataFrame:
    """Live path: reports joined to CURRENT scout reputation (what the backend does)."""
    t = live_tables(source)
    rep = t["syn_scouts"][["scout_id", "reputation"]]
    return t["syn_scout_reports"].merge(rep, on="scout_id", how="left")
