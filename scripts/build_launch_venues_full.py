"""Build data/launch_venues_full.csv: the 35 launch venues plus OSM name/hours.

Usage: python -I scripts/build_launch_venues_full.py [--db data/manhattan_bars.db] [--out data/launch_venues_full.csv]

Reads data/manhattan_bars.db read-only (CONTRACTS v2 §D). The output is real public
data (SLA licences, OSM, 311 counts), so it has no is_synthetic column. Deploys use
this CSV instead of the 39 MB database.
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = [
    "license_id", "name", "display_name", "osm_name", "address", "zip", "lat", "lon",
    "venue_type", "neighborhood", "opening_hours", "osm_has_website", "noise_complaints", "osm_id",
]


def title_case(name: str) -> str:
    """Make an SLA legal name readable when OSM has no name ('ATTABOY COCKTAILS LLC' -> 'Attaboy Cocktails')."""
    words = [w for w in name.replace(",", " ").split() if w.upper() not in {"LLC", "INC", "CORP", "LTD", "CO", "INC."}]
    return " ".join(w.capitalize() if w.isupper() else w for w in words) or name


def build(db: Path, launch_csv: Path) -> list[dict]:
    with launch_csv.open(newline="") as f:
        launch = list(csv.DictReader(f))
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = []
    for v in launch:
        lid = v["license_id"]
        ven = con.execute("SELECT neighborhood, osm_id FROM venues WHERE license_id = ?", (lid,)).fetchone()
        osm_id = (ven["osm_id"] if ven and ven["osm_id"] else v.get("osm_id")) or ""
        osm = con.execute(
            "SELECT name, opening_hours, website FROM osm_venues WHERE osm_id = ?", (osm_id,)
        ).fetchone() if osm_id else None
        osm_name = (osm["name"] if osm and osm["name"] else "") or ""
        rows.append({
            "license_id": lid,
            "name": v["name"],
            "display_name": osm_name or title_case(v["name"]),
            "osm_name": osm_name,
            "address": v["address"],
            "zip": v["zip"],
            "lat": v["lat"],
            "lon": v["lon"],
            "venue_type": v["venue_type"],
            "neighborhood": (ven["neighborhood"] if ven else "") or "",
            "opening_hours": (osm["opening_hours"] if osm else "") or "",
            "osm_has_website": int(bool(osm and osm["website"])),
            "noise_complaints": v["noise_complaints"],
            "osm_id": osm_id,
        })
    con.close()
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", type=Path, default=ROOT / "data/manhattan_bars.db")
    ap.add_argument("--launch", type=Path, default=ROOT / "data/launch_venues.csv")
    ap.add_argument("--out", type=Path, default=ROOT / "data/launch_venues_full.csv")
    a = ap.parse_args()
    if not a.db.exists():
        print(f"missing {a.db}; run src/build_db.py first", file=sys.stderr)
        return 1
    rows = build(a.db, a.launch)
    with a.out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} venues -> {a.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
