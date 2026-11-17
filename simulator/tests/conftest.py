"""Shared fixtures: a quick build (small preset, --nights 3) into a temp folder whose path contains 'synthetic'."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root, so `import simulator` works under -I

from simulator import build as build_mod  # noqa: E402
from simulator import schema  # noqa: E402


def run_build(tmp: Path, seed: int = 42, nights: int = 3, preset: str = "small") -> dict:
    d = tmp / "synthetic_live"
    r = build_mod.build(seed=seed, out=str(tmp / "live_sim.db"), nights=nights, preset=preset, csv_dir=str(d))
    r["dir"] = d
    return r


@pytest.fixture(scope="session")
def small(tmp_path_factory) -> dict:
    tmp = tmp_path_factory.mktemp("run_a")
    r = run_build(tmp)
    r["tables"] = {n: pd.read_csv(r["dir"] / f"{n}.csv", dtype={"venue_id": str, "home_venue_id": str,
                                                                "as_of_date": str}) for n in schema.TABLES}
    r["db"] = tmp / "live_sim.db"
    return r
