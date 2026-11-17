"""Normalise inputs: lists of dicts or DataFrames -> list of plain dicts, NaN -> None."""
from __future__ import annotations

import math
from typing import Any, Iterable

import numpy as np
import pandas as pd


def clean(v: Any) -> Any:
    """numpy scalars -> python, NaN/NaT/pd.NA -> None."""
    if v is None:
        return None
    if v is pd.NA or v is pd.NaT:
        return None
    if isinstance(v, np.generic):
        v = v.item()
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def rows(data: Any) -> list[dict]:
    """Accept None, a DataFrame, a dict, or an iterable of dicts."""
    if data is None:
        return []
    if isinstance(data, pd.DataFrame):
        recs = data.to_dict(orient="records")
    elif isinstance(data, dict):
        recs = [data]
    else:
        recs = list(data)
    return [{k: clean(v) for k, v in r.items()} for r in recs]


def num(v: Any) -> float | None:
    v = clean(v)
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def truthy(v: Any) -> bool:
    v = clean(v)
    if v is None:
        return False
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "yes", "t"}
    return bool(v)


def split_genres(v: Any) -> list[str]:
    v = clean(v)
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return [str(g).strip().lower() for g in v if str(g).strip()]
    return [g.strip().lower() for g in str(v).split("|") if g.strip()]


def round_half_up(x: float, nd: int = 0) -> float:
    m = 10 ** nd
    return math.floor(x * m + 0.5) / m


def by_key(items: Iterable[dict], key: str = "venue_id") -> dict:
    return {r[key]: r for r in items if r.get(key) is not None}
