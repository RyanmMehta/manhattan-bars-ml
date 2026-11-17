"""Existing-pipeline smoke test: run src/simulate.py --n 100 against a temp copy of the DB.

Usage: python -I scripts/integration/pipeline_smoke.py
simulate.py writes into ROOT/data/manhattan_bars.db, so we copy src/ + the DB into a temp
tree and run it there; the committed DB is never touched.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)
    shutil.copytree(ROOT / "src", tmp / "src")
    (tmp / "data").mkdir()
    shutil.copy(ROOT / "data/manhattan_bars.db", tmp / "data/manhattan_bars.db")
    p = subprocess.run([sys.executable, "-I", "src/simulate.py", "--method", "independent", "--n", "100"],
                       cwd=tmp, capture_output=True, text=True)
    print(p.stdout[-500:], p.stderr[-1500:], sep="\n")
    sys.exit(p.returncode)
