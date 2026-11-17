"""CLI. Default action is the fixed build (CONTRACTS v2.2 §J):

    python -m simulator --seed 42 --out data/live_sim.db [--nights N]
    python -m simulator extract-inputs
    python -m simulator validate [--csv-dir data/synthetic_live]
    python -m simulator replay --now 2026-11-14T23:30:00-05:00 [--venue ID] [--shift-to 2026-11-17]

Also runs without installing: `python -I simulator ...` from the repo root.
"""
from __future__ import annotations

import sys

if __package__ in (None, ""):  # executed as `python -I simulator` (directory); make the package importable
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from simulator.cli import main
else:
    from .cli import main

if __name__ == "__main__":
    sys.exit(main())
