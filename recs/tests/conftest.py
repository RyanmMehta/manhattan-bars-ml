# SYNTHETIC: fixtures and golden vectors are synthetic; real pilot data replaces nothing here (tests stay synthetic).
import json
from pathlib import Path

import pandas as pd
import pytest

HERE = Path(__file__).parent
REPO = HERE.parent.parent
NOW = "2026-11-14T23:30:00-05:00"


def golden(name):
    return json.loads((HERE / "golden_recs_derived" / f"{name}.json").read_text())


@pytest.fixture(scope="session")
def fx():
    d = HERE / "fixtures" / "synthetic"
    return {
        "venues": pd.read_csv(d / "venues.csv"),
        "scouts": pd.read_csv(d / "scouts.csv"),
        "reports": pd.read_csv(d / "scout_reports.csv").merge(
            pd.read_csv(d / "scouts.csv")[["scout_id", "reputation"]], on="scout_id", how="left"),
        "updates": pd.read_csv(d / "venue_updates.csv"),
    }


@pytest.fixture(scope="session")
def prefs():
    return json.loads((REPO / "recs" / "examples" / "prefs_contract.json").read_text())


def pytest_configure(config):
    config.addinivalue_line("markers", "db: needs data/manhattan_bars.db or data/live_sim.db")
