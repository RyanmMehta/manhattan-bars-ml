"""The one place that reads the clock or parses `now` (RULES §4)."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")


class NaiveTimeError(ValueError):
    pass


def parse_ts(value: str | datetime) -> datetime:
    """ISO 8601 string -> aware UTC datetime. Naive input is rejected."""
    if isinstance(value, datetime):
        dt = value
    else:
        s = value.strip().replace(" ", "+") if "T" in value else value.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        raise NaiveTimeError(f"timestamp has no UTC offset: {value!r}")
    return dt.astimezone(UTC)


def server_now() -> datetime:
    return datetime.now(UTC)


def parse_now(value: str | None, demo_now: str | None = None) -> datetime:
    """query `now` -> DEMO_NOW -> server clock. Always aware UTC."""
    if value:
        return parse_ts(value)
    if demo_now:
        return parse_ts(demo_now)
    return server_now()


def to_ny_iso(dt: datetime) -> str:
    return dt.astimezone(NY).isoformat(timespec="seconds")


def night_start(now: datetime) -> datetime:
    """18:00 ET of the night containing `now` (a night runs 18:00 -> 12:00 next day)."""
    from .config import NIGHT_START_HOUR

    local = now.astimezone(NY)
    day = local.date() if local.hour >= 12 else local.date() - timedelta(days=1)
    return datetime(day.year, day.month, day.day, NIGHT_START_HOUR, tzinfo=NY).astimezone(UTC)


def minutes_between(earlier: datetime, later: datetime) -> float:
    return (later - earlier).total_seconds() / 60.0
