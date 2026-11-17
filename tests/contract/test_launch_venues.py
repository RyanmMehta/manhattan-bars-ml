"""data/launch_venues_full.csv (integration, v2 §D) matches data/launch_venues.csv."""
import csv


def test_launch_full_matches_launch(root, launch_ids):
    with (root / "data/launch_venues_full.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert {r["license_id"] for r in rows} == launch_ids
    assert len(rows) == 35
    for r in rows:
        assert r["display_name"]
        assert 40.70 < float(r["lat"]) < 40.73 and -74.0 < float(r["lon"]) < -73.97
        assert r["zip"] == "10002"
