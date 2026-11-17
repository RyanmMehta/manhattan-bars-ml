"""Swap switch (INCLUDE_SYNTHETIC=0) and eval-only truth tables (v2 §E). Runs the backend in a subprocess
so env vars apply at import time."""
from __future__ import annotations

import os
import re
import shutil
import sqlite3
import subprocess
import sys
import textwrap

import pytest

from tests.contract.constants import DEMO_NOW

PROBE = textwrap.dedent("""
    import json, sys
    sys.path.insert(0, %(root)r)
    from tests.conftest import _load_app
    from fastapi.testclient import TestClient
    out = {}
    with TestClient(_load_app()) as c:
        for p in ["/api/health", "/api/venues?now=%(now)s", "/api/heatmap?now=%(now)s",
                  "/api/scouts/leaderboard?now=%(now)s", "/api/bounties?now=%(now)s"]:
            r = c.get(p); out[p] = [r.status_code, r.json(), r.headers.get("x-data")]
        r = c.post("/api/recommend?now=%(now)s", json={"lat": 40.7203, "lon": -73.9881, "max_distance_km": 1.5})
        out["recommend"] = [r.status_code, r.json(), r.headers.get("x-data")]
    print(json.dumps(out))
""")


def probe(root, env):
    if not (root / "backend").is_dir():
        pytest.skip("backend/ not merged yet")
    full = {**os.environ, "DEMO_NOW": DEMO_NOW, **env}
    p = subprocess.run([sys.executable, "-c", PROBE % {"root": str(root), "now": DEMO_NOW}], cwd=root,
                       env=full, capture_output=True, text=True, timeout=300)
    assert p.returncode == 0, p.stderr[-2000:]
    import json
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_include_synthetic_off(root, live_db, tmp_path):
    out = probe(root, {"INCLUDE_SYNTHETIC": "0", "LIVE_SIM_DB": str(root / "data/live_sim.db"),
                       "DATABASE_URL": f"sqlite:///{tmp_path/'app.db'}"})
    for path, (code, body, _xdata) in out.items():
        assert code == 200, (path, body)
    assert out["/api/health"][1]["data"] == "real"
    for v in out["/api/venues?now=" + DEMO_NOW][1]:
        st = v.get("state") or {}
        assert not st.get("n_reports"), "synthetic reports leaked with INCLUDE_SYNTHETIC=0"
    assert out["/api/scouts/leaderboard?now=" + DEMO_NOW][1] == []


def test_api_works_without_truth_tables(root, live_db, tmp_path):
    db = tmp_path / "live_sim_no_truth.db"
    shutil.copy(root / "data/live_sim.db", db)
    con = sqlite3.connect(db)
    con.execute("DROP TABLE IF EXISTS syn_true_state")
    con.execute("DROP TABLE IF EXISTS syn_scout_truth")
    con.commit()
    con.close()
    out = probe(root, {"INCLUDE_SYNTHETIC": "1", "LIVE_SIM_DB": str(db),
                       "DATABASE_URL": f"sqlite:///{tmp_path/'app.db'}"})
    for path, (code, body, _x) in out.items():
        assert code == 200, (path, str(body)[:300])


TRUTH = re.compile(r"syn_true_state|syn_scout_truth")


def test_truth_tables_not_referenced_by_runtime(root):
    hits = []
    for folder in ["backend", "recs"]:
        base = root / folder
        if not base.is_dir():
            continue
        for f in base.rglob("*.py"):
            rel = f.relative_to(root).as_posix()
            if re.search(r"(^|/)(tests?|eval\w*|evaluation)(/|_|\.py$)|/test_", rel):
                continue
            for i, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
                if TRUTH.search(line) and not line.lstrip().startswith("#"):
                    hits.append(f"{rel}:{i}: {line.strip()[:120]}")
    assert not hits, "evaluation-only tables read by runtime code:\n" + "\n".join(hits)


def test_final_reputation_not_joined_in_eval(root):
    """Evaluation code that replays past nights must use syn_scout_reputation_history."""
    base = root / "recs"
    if not base.is_dir():
        pytest.skip("recs/ not merged")
    offenders = []
    for f in base.rglob("*.py"):
        rel = f.relative_to(root).as_posix()
        if "eval" not in rel and "train" not in rel:
            continue
        txt = f.read_text(errors="ignore")
        if "syn_scouts" in txt and "reputation" in txt and "syn_scout_reputation_history" not in txt:
            offenders.append(rel)
    assert not offenders, offenders
