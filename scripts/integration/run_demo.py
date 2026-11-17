"""Run the full app locally at the demo time: backend (uvicorn) + frontend (vite dev, live API).

Usage: python -I scripts/integration/run_demo.py [--api-port 8000] [--web-port 5173] [--now ISO]
Ctrl-C stops both.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)


def app_spec() -> str:
    import importlib
    from tests.conftest import APP_CANDIDATES
    for c in ([os.environ["BACKEND_APP"]] if os.environ.get("BACKEND_APP") else APP_CANDIDATES):
        mod, _, attr = c.partition(":")
        try:
            if hasattr(importlib.import_module(mod), attr):
                return c
        except ModuleNotFoundError:
            continue
    sys.exit("backend app not found (is nightlife/backend merged?)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-port", type=int, default=8000)
    ap.add_argument("--web-port", type=int, default=5173)
    ap.add_argument("--now", default="2026-11-14T23:30:00-05:00")
    a = ap.parse_args()
    web = f"http://127.0.0.1:{a.web_port}"
    env = {**os.environ, "LIVE_SIM_DB": str(ROOT / "data/live_sim.db"), "DEMO_NOW": a.now,
           "INCLUDE_SYNTHETIC": "1", "FEATURE_ROUTING": "1", "FEATURE_HEATMAP": "1",
           "CORS_ORIGINS": f"{web},http://localhost:{a.web_port}"}
    if (ROOT / "backend/alembic.ini").exists():
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT / "backend", env=env, check=True)
    api = subprocess.Popen([sys.executable, "-m", "uvicorn", app_spec(), "--port", str(a.api_port)], env=env)
    fenv = {**os.environ, "VITE_API_BASE": f"http://127.0.0.1:{a.api_port}/api", "VITE_API_MODE": "live",
            "VITE_DEMO_NOW": a.now, "VITE_FEATURE_ROUTING": "1", "VITE_FEATURE_HEATMAP": "1"}
    print(f"\n  backend  http://127.0.0.1:{a.api_port}/api/health\n  frontend {web}/\n", flush=True)
    try:
        return subprocess.call(["npx", "vite", "--host", "127.0.0.1", "--port", str(a.web_port), "--strictPort"],
                               cwd=ROOT / "frontend", env=fenv)
    except KeyboardInterrupt:
        return 0
    finally:
        api.terminate()


if __name__ == "__main__":
    sys.exit(main())
