"""Start backend (uvicorn) + built frontend (vite preview) for e2e, unless BASE_URL/API_URL are given."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
API_PORT = int(os.environ.get("E2E_API_PORT", 8765))
WEB_PORT = int(os.environ.get("E2E_WEB_PORT", 4173))


def wait_port(port, proc, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            raise RuntimeError(f"server on {port} exited with {proc.returncode}")
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.5)
    raise TimeoutError(f"port {port} not up after {timeout}s")


def app_spec():
    sys.path.insert(0, str(ROOT))
    from tests.conftest import APP_CANDIDATES
    import importlib
    for c in ([os.environ["BACKEND_APP"]] if os.environ.get("BACKEND_APP") else APP_CANDIDATES):
        mod, _, attr = c.partition(":")
        try:
            if hasattr(importlib.import_module(mod), attr):
                return c
        except ModuleNotFoundError:
            continue
    raise RuntimeError("backend app not found")


@pytest.fixture(scope="session")
def servers(tmp_path_factory):
    if os.environ.get("BASE_URL"):
        yield {"web": os.environ["BASE_URL"].rstrip("/"), "api": os.environ.get("API_URL", "").rstrip("/")}
        return
    if not (ROOT / "backend").is_dir() or not (ROOT / "frontend/package.json").exists():
        pytest.skip("backend/ and frontend/ must both be merged for e2e")
    if not (ROOT / "data/live_sim.db").exists():
        pytest.skip("data/live_sim.db missing (make data)")
    from tests.contract.constants import DEMO_NOW
    tmp = tmp_path_factory.mktemp("e2e")
    api_url = f"http://127.0.0.1:{API_PORT}"
    env = {**os.environ, "LIVE_SIM_DB": str(ROOT / "data/live_sim.db"), "DEMO_NOW": DEMO_NOW,
           "INCLUDE_SYNTHETIC": "1", "CORS_ORIGINS": f"http://127.0.0.1:{WEB_PORT},http://localhost:{WEB_PORT}",
           "FEATURE_ROUTING": "1", "FEATURE_HEATMAP": "1",
           "DATABASE_URL": os.environ.get("E2E_DATABASE_URL", f"sqlite:///{tmp/'app.db'}")}
    if (ROOT / "backend/alembic.ini").exists():  # real twin tables (alembic upgrade head)
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT / "backend", env=env, check=True,
                       capture_output=True)
    api = subprocess.Popen([sys.executable, "-m", "uvicorn", app_spec(), "--port", str(API_PORT)],
                           cwd=ROOT, env=env, stdout=open(tmp / "api.log", "w"), stderr=subprocess.STDOUT)
    fe = ROOT / "frontend"
    fenv = {**os.environ, "VITE_API_BASE": f"{api_url}/api", "VITE_API_MODE": "live", "VITE_DEMO_NOW": DEMO_NOW,
            "VITE_FEATURE_ROUTING": "1", "VITE_FEATURE_HEATMAP": "1"}
    if not (fe / "node_modules").exists():
        subprocess.run(["npm", "ci", "--no-audit", "--no-fund"], cwd=fe, check=True)
    subprocess.run(["npm", "run", "build"], cwd=fe, env=fenv, check=True)
    web = subprocess.Popen(["npx", "vite", "preview", "--host", "127.0.0.1", "--port", str(WEB_PORT), "--strictPort"],
                           cwd=fe, env=fenv, stdout=open(tmp / "web.log", "w"), stderr=subprocess.STDOUT)
    try:
        wait_port(API_PORT, api)
        wait_port(WEB_PORT, web)
        yield {"web": f"http://127.0.0.1:{WEB_PORT}", "api": api_url, "logs": tmp}
    finally:
        for p in (web, api):
            p.terminate()
            try:
                p.wait(10)
            except subprocess.TimeoutExpired:
                p.kill()
