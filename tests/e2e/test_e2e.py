"""Browser smoke test: runs tests/e2e/smoke.cjs (Node Playwright, preinstalled Chromium) against the servers."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).parent


def run_smoke(servers, out):
    env = {**os.environ, "BASE_URL": servers["web"], "API_URL": servers.get("api", ""), "OUT_DIR": str(out),
           "NODE_PATH": os.environ.get("NODE_PATH", "/opt/node-tools/node_modules")}
    p = subprocess.run(["node", str(HERE / "smoke.cjs")], env=env, capture_output=True, text=True, timeout=300)
    print(p.stdout[-4000:])
    print(p.stderr[-4000:])
    result = json.loads((out / "result.json").read_text()) if (out / "result.json").exists() else {}
    return p.returncode, result


def test_demo_path(servers, tmp_path):
    code, result = run_smoke(servers, tmp_path)
    failed = [s for s in result.get("steps", []) if not s["ok"]]
    assert code == 0 and not failed, json.dumps(failed or result, indent=1)[:4000]
