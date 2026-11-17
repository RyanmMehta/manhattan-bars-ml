"""Tiny OSM `opening_hours` parser for the simple forms only.

Supported: "24/7", and ';'-separated rules like "Mo-Th 17:00-02:00", "Fr,Sa 16:00-04:00", "Su off".
Anything else -> unknown (None), which never excludes a venue (specs §5.9).
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

from .timeutil import to_dt

DAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
_RULE = re.compile(r"^(?P<days>[A-Za-z,\- ]+?)\s+(?P<spans>off|closed|\d{1,2}:\d{2}-\d{1,2}:\d{2}(?:\s*,\s*\d{1,2}:\d{2}-\d{1,2}:\d{2})*)$")


def _days(spec: str) -> list[int] | None:
    out: list[int] = []
    for part in spec.replace(" ", "").split(","):
        if "-" in part:
            a, b = part.split("-", 1)
            if a not in DAYS or b not in DAYS:
                return None
            i, j = DAYS.index(a), DAYS.index(b)
            out += [(i + k) % 7 for k in range(((j - i) % 7) + 1)]
        elif part in DAYS:
            out.append(DAYS.index(part))
        else:
            return None
    return out


def _mins(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def parse(s: str | None):
    """Return {weekday: [(open_min, close_min)]} (close may exceed 1440 for overnight), 'always', or None."""
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if s == "24/7":
        return "always"
    s = re.sub(r"(?<=\d),\s*(?=(?:Mo|Tu|We|Th|Fr|Sa|Su)\b)", ";", s)  # "Tu-Th 17:00-24:00, Fr-Sa ..." rule groups
    table: dict[int, list[tuple[int, int]]] = {d: [] for d in range(7)}
    for rule in [r.strip() for r in s.split(";") if r.strip()]:
        m = _RULE.match(rule)
        if not m:
            return None
        days = _days(m.group("days"))
        if not days:
            return None
        spans = m.group("spans")
        for d in days:
            table[d] = []  # later rules override earlier ones for the same day (OSM semantics)
            if spans in ("off", "closed"):
                continue
            for sp in spans.split(","):
                a, b = sp.strip().split("-")
                o, c = _mins(a), _mins(b)
                if c <= o:
                    c += 1440
                table[d].append((o, c))
    return table


def is_open(s: str | None, when) -> bool | None:
    """True/False if `s` parses, else None (unknown)."""
    t = parse(s)
    if t is None:
        return None
    if t == "always":
        return True
    dt: datetime = to_dt(when)
    m = dt.hour * 60 + dt.minute
    wd = dt.weekday()
    for o, c in t[wd]:
        if o <= m < c:
            return True
    prev = (wd - 1) % 7
    for o, c in t[prev]:
        if c > 1440 and m < c - 1440:
            return True
    return False
