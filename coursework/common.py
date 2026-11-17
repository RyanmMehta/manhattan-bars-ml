"""Tiny shared helpers for both coursework exercises.

What it does: gives every script the repo ROOT path, one function to seed every random
number generator, and one function to open a SQLite database READ-ONLY.
How to use:   from coursework.common import ROOT, set_seed, connect_read_only
"""
import os
import random
import sqlite3
from pathlib import Path

import numpy as np

# parents[0] = coursework/, parents[1] = repo root.
ROOT = Path(__file__).resolve().parents[1]

# Real public-data DB built by src/ (SLA licences etc.). We only ever read it.
VENUE_DB = ROOT / "data" / "manhattan_bars.db"

# SYNTHETIC: live-sim's output DB; replace with the real backend DB (tables without syn_).
LIVE_SIM_DB = Path(os.environ.get("LIVE_SIM_DB", ROOT / "data" / "live_sim.db"))


def set_seed(seed: int) -> None:
    """Seed Python, numpy and (if installed) torch so runs are repeatable."""
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch  # imported here so the churn code does not need torch
        torch.manual_seed(seed)
    except ImportError:
        pass


def connect_read_only(path: Path) -> sqlite3.Connection:
    """Open a SQLite file in read-only mode (mode=ro), so we can never change it by mistake."""
    if not Path(path).exists():
        raise FileNotFoundError(f"database not found: {path}")
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)
