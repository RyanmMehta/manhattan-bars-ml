"""Runs only when a real live-sim DB exists (data/live_sim.db, or BACKEND_TEST_LIVE_SIM_DB).
SYNTHETIC: live-sim output; checks schema + every read endpoint at DEMO_NOW."""

import os
from pathlib import Path

import pytest

from app.simdb import read_schema, schema_problems
from tests.fixtures.golden import PREFS

ROOT = Path(__file__).resolve().parents[2]
SIM = Path(os.environ.get("BACKEND_TEST_LIVE_SIM_DB", ROOT / "data" / "live_sim.db"))
pytestmark = pytest.mark.skipif(not SIM.exists(), reason="no real live_sim.db")


def test_schema_matches_contract():
    assert schema_problems(read_schema(str(SIM))) == []


def test_endpoints_on_real_sim(make_client):
    c = make_client(live_sim_db=str(SIM))
    assert c.get("/api/health").json()["data"] == "synthetic"
    cards = c.get("/api/venues").json()
    assert len(cards) == 35
    assert any(x["state"]["display"] == "show" for x in cards)
    for url in [
        "/api/heatmap?by=hour",
        "/api/scouts/leaderboard",
        "/api/bounties",
        f"/api/venues/{cards[0]['venue_id']}",
    ]:
        assert c.get(url).status_code == 200, url
    assert c.post("/api/recommend", json=PREFS).status_code == 200
    assert c.post("/api/plan-night", json=PREFS).status_code == 200
