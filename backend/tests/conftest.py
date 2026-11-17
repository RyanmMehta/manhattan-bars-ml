from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.fixture_sim import build_fixture_sim
from app.main import create_app
from app.models import Base

DEMO_NOW = "2026-11-14T23:30:00-05:00"
FIXTURE_DIR = Path(__file__).parent / "fixtures" / "synthetic"
FIXTURE_DB = FIXTURE_DIR / "fixture_live_sim.db"
ROOT = Path(__file__).resolve().parents[2]
VENUE = "0370-24-138636"  # Attaboy, first launch venue (a "hot" fixture venue)


@pytest.fixture(scope="session")
def fixture_sim() -> str:
    # SYNTHETIC: tiny stand-in for live-sim's data/live_sim.db (tests only)
    if not FIXTURE_DB.exists():
        build_fixture_sim(str(FIXTURE_DB), str(ROOT / "data" / "launch_venues.csv"))
    return str(FIXTURE_DB)


@pytest.fixture
def make_client(tmp_path, fixture_sim):
    made: list[TestClient] = []

    def _make(**overrides) -> TestClient:
        base = dict(
            database_url=f"sqlite:///{tmp_path}/app_{len(list(tmp_path.iterdir()))}.db",
            live_sim_db=fixture_sim,
            public_db_path=str(tmp_path / "no_public.db"),
            launch_venues_full_csv=str(tmp_path / "no_full.csv"),
            manual_attributes_csv=str(tmp_path / "no_manual.csv"),
            demo_now=DEMO_NOW,
            recs_mode="stub",
            allow_write_now=True,
            allow_fixture_sim=False,
            admin_token="test-admin",
            log_level="WARNING",
        )
        base.update(overrides)
        settings = Settings(**base)
        app = create_app(settings)
        Base.metadata.create_all(app.state.ctx.db.engine)
        c = TestClient(app)
        made.append(c)
        return c

    yield _make
    for c in made:
        c.app.state.ctx.db.engine.dispose()


@pytest.fixture
def client(make_client) -> TestClient:
    return make_client()


def login(client: TestClient, role: str, venue_id: str | None = None, name: str = "Tester") -> dict:
    body = {"display_name": name, "role": role}
    if venue_id:
        body["venue_id"] = venue_id
    r = client.post("/api/auth/demo-login", json=body)
    assert r.status_code == 201, r.text
    out = r.json()
    out["headers"] = {"Authorization": f"Bearer {out['token']}"}
    return out
