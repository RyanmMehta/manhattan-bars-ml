"""Per-stage random generators from one master seed (stable: keyed by sha256 of the stage name)."""
from __future__ import annotations

import hashlib

import numpy as np


def stage_rng(seed: int, stage: str) -> np.random.Generator:
    """Independent Generator for `stage`; editing one stage never shifts another's stream."""
    key = int.from_bytes(hashlib.sha256(stage.encode()).digest()[:8], "big")
    return np.random.default_rng(np.random.SeedSequence([int(seed), key]))
