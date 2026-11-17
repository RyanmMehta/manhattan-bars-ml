"""Venue catalog (real public data) + attributes. Public data is static, so it is loaded
once read-only into memory; works the same with SQLite or Postgres app DBs."""

import csv
import re
import sqlite3
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import config as C
from .sources import Sources

_SUFFIX = re.compile(r"[\s,]+(LLC|L\.L\.C\.|INC\.?|CORP\.?|CORPORATION|LTD\.?|CO\.?)\s*$", re.I)


def clean_sla_name(name: str) -> str:
    n = name or ""
    while _SUFFIX.search(n):
        n = _SUFFIX.sub("", n)
    return n.strip().title()


def _num(v: object) -> float | None:
    if v in (None, ""):
        return None
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _venue(row: dict, is_launch: bool) -> dict:
    osm_name = row.get("osm_name") or row.get("display_name")
    noise = _num(row.get("noise_complaints"))
    return {
        "venue_id": row["license_id"],
        "name": row.get("name") or "",
        "display_name": osm_name or clean_sla_name(row.get("name") or ""),
        "address": row.get("address"),
        "lat": float(row["lat"]),
        "lon": float(row["lon"]),
        "neighborhood": row.get("neighborhood") or None,
        "venue_type": row.get("venue_type"),
        "osm_id": row.get("osm_id") or None,
        "osm_opening_hours": row.get("opening_hours") or None,
        "noise_complaints": None if noise is None else int(noise),
        "is_launch": is_launch,
    }


@dataclass
class Catalog:
    launch: list[dict]
    all_bars: list[dict]
    source: str

    def __post_init__(self) -> None:
        self.by_id = {v["venue_id"]: v for v in self.all_bars}
        for v in self.launch:
            self.by_id[v["venue_id"]] = v


def _public_rows(db_path: str, where: str, params: tuple = ()) -> list[dict]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        sql = (
            "SELECT b.license_id, b.name, b.address, b.lat, b.lon, b.neighborhood, b.venue_type,"
            " b.osm_id, b.noise_complaints, o.name AS osm_name, o.opening_hours"
            " FROM v_bars b LEFT JOIN osm_venues o ON o.osm_id = b.osm_id"
            f" WHERE b.lat IS NOT NULL {where}"
        )
        return [dict(r) for r in conn.execute(sql, params)]
    finally:
        conn.close()


@lru_cache
def load_catalog(full_csv: str, launch_csv: str, public_db: str) -> Catalog:
    with open(launch_csv, newline="") as f:
        launch_rows = list(csv.DictReader(f))
    launch_ids = [r["license_id"] for r in launch_rows]
    public = Path(public_db).exists()
    all_bars = (
        [_venue(r, r["license_id"] in set(launch_ids)) for r in _public_rows(public_db, "")]
        if public
        else []
    )
    if Path(full_csv).exists():
        with open(full_csv, newline="") as f:
            launch = [_venue(r, True) for r in csv.DictReader(f)]
        source = "launch_venues_full.csv"
    elif public:
        by = {v["venue_id"]: v for v in all_bars}
        launch = [by[i] for i in launch_ids if i in by]
        source = "manhattan_bars.db"
    else:
        launch = [_venue(r, True) for r in launch_rows]
        source = "launch_venues.csv"
    if not all_bars:
        all_bars = list(launch)
    return Catalog(launch=launch, all_bars=all_bars, source=source)


def complaint_risk(v: dict) -> dict:
    n = v.get("noise_complaints")
    if n is None:
        level = None
    elif n < C.NOISE_RISK_BANDS[0]:
        level = "low"
    elif n < C.NOISE_RISK_BANDS[1]:
        level = "medium"
    else:
        level = "high"
    return {"label": "311 noise-complaint risk", "noise_complaints_3y": n, "level": level}


ATTR_COLS = [
    "venue_id",
    "genres",
    "style",
    "has_dance_floor",
    "typical_cover_usd",
    "capacity",
    "price_level",
    "is_claimed",
    "opening_hours",
    "is_synthetic",
]


@lru_cache
def _manual_attributes(path: str, mtime: float) -> dict[str, dict]:
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    out = {}
    for r in rows:
        out[r["venue_id"]] = {c: (r.get(c) or None) for c in ATTR_COLS} | {"is_synthetic": 0}
    return out


def load_attributes(session: Session, src: Sources, manual_csv: str) -> dict[str, dict]:
    """Manual CSV (is_synthetic=0) > real venue_attributes > syn_venue_attributes (v2 §D)."""
    out: dict[str, dict] = {}
    # SYNTHETIC: syn_venue_attributes until data/venue_attributes_manual.csv is filled in
    for r in session.execute(text(f"SELECT * FROM {src.union('venue_attributes')} a")).mappings():
        r = dict(r)
        if r["venue_id"] in out and out[r["venue_id"]]["is_synthetic"] == 0:
            continue
        out[r["venue_id"]] = r
    p = Path(manual_csv)
    if p.exists():
        out.update(_manual_attributes(str(p), p.stat().st_mtime))
    for r in out.values():
        for k in ("has_dance_floor", "capacity", "price_level", "is_claimed"):
            if r.get(k) not in (None, ""):
                r[k] = int(float(r[k]))
        if r.get("typical_cover_usd") not in (None, ""):
            r["typical_cover_usd"] = float(r["typical_cover_usd"])
        r["is_synthetic"] = int(r.get("is_synthetic") or 0)
    return out
