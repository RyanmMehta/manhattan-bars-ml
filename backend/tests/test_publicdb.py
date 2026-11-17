from pathlib import Path

import pytest

from app.genres import VENDORED_GENRES, load_genres
from app.repo.venues import clean_sla_name, load_catalog

ROOT = Path(__file__).resolve().parents[2]
PUB = ROOT / "data" / "manhattan_bars.db"


@pytest.mark.publicdb
@pytest.mark.skipif(not PUB.exists(), reason="public DB not present")
def test_public_catalog(make_client):
    cat = load_catalog("/nonexistent.csv", str(ROOT / "data" / "launch_venues.csv"), str(PUB))
    assert len(cat.launch) == 35 and cat.source == "manhattan_bars.db"
    assert len(cat.all_bars) > 1500
    assert all(v["display_name"] for v in cat.launch)
    c = make_client(public_db_path=str(PUB))
    assert c.get("/api/venues").headers["X-Total-Count"] == "35"
    assert int(c.get("/api/venues?launch_only=false").headers["X-Total-Count"]) > 1500


def test_full_csv_preferred(tmp_path):
    p = tmp_path / "full.csv"
    p.write_text(
        "license_id,name,address,lat,lon,noise_complaints,osm_name,opening_hours\n"
        "X-1,FOO BAR LLC,1 MAIN ST,40.7,-73.9,3,Foo Bar,Mo-Su 18:00-02:00\n"
    )
    cat = load_catalog(str(p), str(ROOT / "data" / "launch_venues.csv"), "/nonexistent.db")
    assert cat.source == "launch_venues_full.csv" and cat.launch[0]["display_name"] == "Foo Bar"


def test_clean_name():
    assert clean_sla_name("ATTABOY COCKTAILS LLC") == "Attaboy Cocktails"
    assert clean_sla_name("FOO, INC.") == "Foo"


def test_genres_json(tmp_path):
    p = tmp_path / "g.json"
    p.write_text('{"genres": [{"slug": "hip-hop"}, {"slug": "jazz"}]}')
    assert load_genres(str(p)) == ("hip-hop", "jazz")
    assert load_genres(str(tmp_path / "none.json")) == tuple(VENDORED_GENRES)
    assert len(VENDORED_GENRES) == 17
