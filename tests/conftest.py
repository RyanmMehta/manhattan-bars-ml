"""Shared test glue (integration-owned).

Fixtures skip cleanly when a workstream hasn't been merged yet, so `make test`
is green at every step of the merge order.

Env:
  LIVE_SIM_DB   path to the generated synthetic DB (default data/live_sim.db)
  API_URL       test a running/deployed backend instead of an in-process TestClient
  BACKEND_APP   "module:attr" of the FastAPI app (auto-detected otherwise)
"""
from __future__ import annotations

import importlib
import os
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.contract.constants import DEMO_NOW  # noqa: E402

LIVE_SIM_DB = Path(os.environ.get("LIVE_SIM_DB", ROOT / "data/live_sim.db"))
APP_CANDIDATES = ["backend.app.main:app", "backend.main:app", "backend.app:app", "backend.api.main:app"]


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def live_db():
    if not LIVE_SIM_DB.exists():
        pytest.skip(f"{LIVE_SIM_DB} not built (run `make data` once live-sim is merged)")
    con = sqlite3.connect(f"file:{LIVE_SIM_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    yield con
    con.close()


@pytest.fixture(scope="session")
def launch_ids() -> set[str]:
    import csv
    with (ROOT / "data/launch_venues.csv").open(newline="") as f:
        return {r["license_id"] for r in csv.DictReader(f)}


@pytest.fixture(scope="session")
def recs():
    if not (ROOT / "recs").is_dir():
        pytest.skip("recs/ not merged yet")
    try:
        return importlib.import_module("recs")
    except Exception as e:  # pragma: no cover - reported as skip so the cause is visible
        pytest.fail(f"recs/ exists but does not import: {e!r}")


def _load_app():
    spec = os.environ.get("BACKEND_APP")
    candidates = [spec] if spec else APP_CANDIDATES
    errors = []
    for c in candidates:
        mod, _, attr = c.partition(":")
        try:
            return getattr(importlib.import_module(mod), attr)
        except ModuleNotFoundError as e:
            errors.append(f"{c}: {e}")
        except AttributeError as e:
            errors.append(f"{c}: {e}")
    raise RuntimeError("could not import backend app: " + "; ".join(errors))


@pytest.fixture(scope="session")
def api():
    """httpx-like client: TestClient in-process, or httpx.Client against API_URL."""
    url = os.environ.get("API_URL")
    if url:
        import httpx
        with httpx.Client(base_url=url.rstrip("/"), timeout=90) as c:
            yield c
        return
    if not (ROOT / "backend").is_dir():
        pytest.skip("backend/ not merged yet")
    os.environ.setdefault("LIVE_SIM_DB", str(LIVE_SIM_DB))
    os.environ.setdefault("DEMO_NOW", DEMO_NOW)
    os.environ.setdefault("INCLUDE_SYNTHETIC", "1")
    from fastapi.testclient import TestClient
    with TestClient(_load_app()) as c:
        yield c


@pytest.fixture(scope="session")
def demo_now() -> str:
    return DEMO_NOW
