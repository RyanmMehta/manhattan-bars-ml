"""Config loading: default.json (+ preset overrides), genre vocabulary, env defaults."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path

PKG = Path(__file__).resolve().parent
CONFIG_DIR = PKG / "config"
REPO = PKG.parent

GENRES: list[str] = json.loads((CONFIG_DIR / "genres.json").read_text())["genres"]
DEMO_NOW: str = os.environ.get("DEMO_NOW", "2026-11-14T23:30:00-05:00")
LIVE_SIM_DB: str = os.environ.get("LIVE_SIM_DB", "data/live_sim.db")


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load(name: str = "default", seed: int = 42, nights: int | None = None, **overrides) -> dict:
    """Load default.json, apply preset `name` (small|demo) and overrides; add seed/nights."""
    cfg = json.loads((CONFIG_DIR / "default.json").read_text())
    if name != "default":
        cfg = _merge(cfg, json.loads((CONFIG_DIR / f"{name}.json").read_text()))
    cfg = _merge(cfg, overrides)
    cfg["seed"] = int(seed)
    if nights is not None:
        cfg["nights"] = int(nights)
    cfg.setdefault("nights", None)
    return cfg


def config_hash(cfg: dict) -> str:
    """sha256 of the canonical JSON config (first 16 hex chars)."""
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:16]
