import hashlib
import sqlite3

import pandas as pd

from conftest import DB, LAUNCH

EXPECTED = {
    "bars.csv": ["venue_id", "name", "address", "zip", "neighborhood", "lat", "lon", "has_coords",
                 "venue_type", "liquor_tier", "latest_grade", "noise_complaints", "complaint_bucket",
                 "high_noise", "density_100m", "density_250m", "years_licensed", "osm_amenity",
                 "osm_closes_late", "is_launch", "is_synthetic"],
    "venue_features_slim.csv": ["venue_id", "venue_type", "neighborhood", "latest_grade", "lat", "lon",
                                "noise_complaints", "high_noise", "density_100m", "mean_score", "is_synthetic"],
    "launch_venues.csv": ["venue_id", "name", "address", "lat", "lon", "venue_type", "latest_grade",
                          "noise_complaints", "osm_id", "launch_rank", "is_synthetic"],
    "neighborhood_summary.csv": ["neighborhood", "n_venues", "n_bars", "n_clubs", "mean_density_100m",
                                 "total_complaints", "complaints_per_bar", "pct_high_noise", "pct_grade_a",
                                 "centroid_lat", "centroid_lon", "is_synthetic"],
    "grade_by_neighborhood.csv": ["neighborhood", "latest_grade", "grade_order", "n", "pct", "is_synthetic"],
}


def read(out, name):
    return pd.read_csv(out / name, dtype={"zip": str})


def test_columns_and_not_synthetic(exported):
    for name, cols in EXPECTED.items():
        df = read(exported, name)
        assert list(df.columns) == cols, name
        assert (df["is_synthetic"] == 0).all(), name


def test_row_counts(exported):
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    n_hoods = con.execute("SELECT COUNT(DISTINCT neighborhood) FROM venues").fetchone()[0]
    n_10002 = con.execute("SELECT COUNT(*) FROM v_bars WHERE zip='10002'").fetchone()[0]
    bars = read(exported, "bars.csv")
    assert len(bars) == 1727
    assert (bars["has_coords"] == 0).sum() == 18
    assert (bars["zip"] == "10002").sum() == n_10002 == 136
    assert len(read(exported, "launch_venues.csv")) == 35
    hoods = read(exported, "neighborhood_summary.csv")
    assert len(hoods) == n_hoods == 15
    assert hoods["n_bars"].sum() == 1727
    assert len(read(exported, "venue_features_slim.csv")) == 5704


def test_launch_in_bars(exported):
    bars = read(exported, "bars.csv")
    launch = read(exported, "launch_venues.csv")
    assert set(launch["venue_id"]) <= set(bars["venue_id"])
    assert bars["is_launch"].sum() == 35
    assert set(pd.read_csv(LAUNCH)["license_id"]) == set(launch["venue_id"])


def test_grades_complete(exported):
    g = read(exported, "grade_by_neighborhood.csv")
    assert g["n"].sum() == 1727
    assert set(g["latest_grade"]) == {"A", "B", "C", "N", "Z", "Not matched"}
    assert g.groupby("neighborhood")["pct"].sum().between(99.9, 100.1).all()


def _hashes(d):
    return {p.relative_to(d): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.rglob("*.csv"))}


def test_deterministic(exported, tmp_path):
    import export_extracts as ex
    ex.export(DB, tmp_path, tmp_path / "synthetic", LAUNCH, None, None, placeholder=True)
    assert _hashes(tmp_path) == _hashes(exported)
