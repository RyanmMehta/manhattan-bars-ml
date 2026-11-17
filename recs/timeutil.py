"""Time helpers: parse `now`, America/New_York, night date."""
from __future__ import annotations

from datetime import datetime, timedelta, date
import math

import pandas as pd

from .config import TZ


def to_dt(x) -> datetime | None:
    """ISO string / datetime / pandas Timestamp -> tz-aware datetime in America/New_York.

    Naive values are assumed to be New York local time.
    """
    if x is None:
        return None
    if isinstance(x, float) and math.isnan(x):
        return None
    if isinstance(x, pd.Timestamp):
        if pd.isna(x):
            return None
        x = x.to_pydatetime()
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return None
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        x = datetime.fromisoformat(s)
    if not isinstance(x, datetime):
        raise TypeError(f"cannot parse time {x!r}")
    if x.tzinfo is None:
        return x.replace(tzinfo=TZ)
    return x.astimezone(TZ)


def iso(dt: datetime | None) -> str | None:
    return None if dt is None else to_dt(dt).isoformat()


def minutes_between(later: datetime, earlier: datetime) -> float:
    return (later - earlier).total_seconds() / 60.0


def night_date(dt) -> date:
    """Nights run 18:00-05:59; early-morning hours belong to the previous date."""
    d = to_dt(dt)
    if d.hour < 6:
        return (d - timedelta(days=1)).date()
    return d.date()
