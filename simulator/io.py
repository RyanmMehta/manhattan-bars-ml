"""Deterministic CSV writing (local ISO timestamps, fixed float format) and manifest.json."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd

from . import schema, timeutil
from .config import config_hash

TS_COLS = {"ts", "joined_at", "last_active_at", "offer_expires_at", "recommended_at", "created_at", "expires_at",
           "claimed_at", "opened_at", "resolved_at", "churned_at", "snapshot_ts"}
INT_COLS = {"distance_m", "dancing", "line_minutes", "cover_usd", "rating", "crowd_true", "dancing_true",
            "line_minutes_true", "occupancy", "n_reports", "vibe_score", "typical_cover_usd", "capacity",
            "price_level", "has_dance_floor", "is_claimed", "points", "reports_count", "cohort_week", "visited",
            "verified_presence", "is_synthetic", "crowd"}


def to_output(df: pd.DataFrame, table: str) -> pd.DataFrame:
    """Contract columns only, timestamps as local ISO strings, nullable ints kept as Int64."""
    cols = schema.SNAPSHOT_COLUMNS if table == "demo_night_snapshots" else schema.TABLES[table]
    out = df[cols].copy()
    for c in cols:
        if c in TS_COLS:
            out[c] = timeutil.to_local_iso(out[c])
        elif c in INT_COLS and not (table == "demo_night_snapshots" and c in ("crowd", "dancing")):
            out[c] = pd.to_numeric(out[c], errors="coerce").round().astype("Int64")
    return out


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, lineterminator="\n", float_format="%.3f")


def git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              cwd=Path(__file__).parent, timeout=5).stdout.strip() or None
    except Exception:  # noqa: BLE001 - manifest field is best-effort
        return None


def write_manifest(out_dir: Path, cfg: dict, files: dict[str, Path], rows: dict[str, int], extra: dict) -> dict:
    """manifest.json: seed, config hash, commit, version, row counts, sha256 per file (+ extra)."""
    from . import __version__
    m = {"generator": "simulator", "version": __version__, "seed": cfg["seed"], "config_hash": config_hash(cfg),
         "git_commit": git_commit(), "nights": extra.pop("nights", None), "is_synthetic": True,
         "rows": rows, "sha256": {k: sha256(p) for k, p in sorted(files.items())}, **extra}
    (out_dir / "manifest.json").write_text(json.dumps(m, indent=2, sort_keys=True) + "\n")
    return m
