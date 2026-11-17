"""Night calendar and time grid: Thu-Sat nights 2026-08-27 -> 2026-11-14, 20:00-03:00 ET.

Internally everything is tz-aware UTC; `to_local_iso` converts to America/New_York
only when writing. DST-safe: the Sat Oct 31 night runs 20:00 EDT -> 03:00 EST.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

TZ = ZoneInfo("America/New_York")
FIRST_NIGHT = date(2026, 8, 27)
LAST_NIGHT = date(2026, 11, 14)
NIGHT_START = time(20, 0)
NIGHT_END = time(3, 0)  # next calendar day
SLOT_MIN = 15


def all_nights() -> list[date]:
    """Every Thu/Fri/Sat between FIRST_NIGHT and LAST_NIGHT (36 nights)."""
    out, d = [], FIRST_NIGHT
    while d <= LAST_NIGHT:
        if d.weekday() in (3, 4, 5):
            out.append(d)
        d += timedelta(days=1)
    return out


def nights(n: int | None = None) -> list[date]:
    """The last n nights (ending Sat Nov 14, so the demo night is always included)."""
    allv = all_nights()
    return allv if not n or n >= len(allv) else allv[-n:]


def night_bounds(d: date) -> tuple[pd.Timestamp, pd.Timestamp]:
    """UTC start/end of night d (20:00 local on d -> 03:00 local on d+1)."""
    start = datetime.combine(d, NIGHT_START, tzinfo=TZ)
    end = datetime.combine(d + timedelta(days=1), NIGHT_END, tzinfo=TZ)
    return pd.Timestamp(start).tz_convert("UTC"), pd.Timestamp(end).tz_convert("UTC")


def slots(d: date) -> pd.DatetimeIndex:
    """15-min UTC slot starts covering night d (end exclusive)."""
    s, e = night_bounds(d)
    return pd.date_range(s, e, freq=f"{SLOT_MIN}min", inclusive="left")


def local_hour(ts) -> "pd.Series | float":
    """Local clock hour as a float on a 20..27 scale (01:30 -> 25.5). Works on Series/Index/Timestamp."""
    if isinstance(ts, pd.Timestamp):
        loc = ts.tz_convert(TZ)
        h = loc.hour + loc.minute / 60
        return h + 24 if h < 12 else h
    loc = pd.DatetimeIndex(ts).tz_convert(TZ)
    h = loc.hour + loc.minute / 60
    return pd.Index(h).where(h >= 12, h + 24).to_numpy(dtype=float)


def to_local_iso(s: pd.Series) -> pd.Series:
    """UTC timestamps -> ISO 8601 strings with America/New_York offset; NaT -> None."""
    loc = pd.to_datetime(s, utc=True).dt.tz_convert(TZ)
    out = loc.dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    out = out.str.replace(r"([+-]\d{2})(\d{2})$", r"\1:\2", regex=True)
    return out.where(loc.notna(), None)


def parse_ts(x) -> pd.Timestamp:
    """Parse an ISO string (any offset) to a UTC Timestamp."""
    t = pd.Timestamp(x)
    if t.tzinfo is None:
        t = t.tz_localize(TZ)
    return t.tz_convert("UTC")


def night_of(ts: pd.Timestamp) -> date:
    """Calendar date of the night a timestamp belongs to (before noon -> previous day)."""
    loc = ts.tz_convert(TZ)
    return (loc - pd.Timedelta(hours=12)).date()
