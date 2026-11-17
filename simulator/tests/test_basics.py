"""Genres, time grid (incl. DST), live-state golden vector G1, opening-hours parser."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from simulator import _live_state, timeutil
from simulator.config import GENRES
from simulator.venues import night_window, parse_hours

CONTRACT_GENRES = ["hip-hop", "r&b", "afrobeats", "latin", "reggaeton", "house", "techno", "edm", "disco", "pop",
                   "top-40", "throwbacks", "indie", "rock", "punk", "jazz", "soul-funk"]


def test_genres_json_matches_contract():
    data = json.loads((Path(__file__).parents[1] / "config" / "genres.json").read_text())
    assert data["version"] == 1 and data["genres"] == CONTRACT_GENRES == GENRES
    assert all(g == g.lower() for g in GENRES) and len(set(GENRES)) == 17


def test_nights_calendar():
    n = timeutil.all_nights()
    assert len(n) == 36 and n[0] == date(2026, 8, 27) and n[-1] == date(2026, 11, 14)
    assert {d.weekday() for d in n} == {3, 4, 5}
    assert timeutil.nights(3)[-1] == date(2026, 11, 14) and len(timeutil.nights(3)) == 3


def test_dst_night_oct31():
    s = timeutil.slots(date(2026, 10, 31))
    assert s.is_monotonic_increasing and len(s) == 32  # 20:00 EDT -> 03:00 EST is 8 real hours
    iso = timeutil.to_local_iso(pd.Series(s))
    assert iso.iloc[0] == "2026-10-31T20:00:00-04:00" and iso.iloc[-1].endswith("-05:00")
    assert len(timeutil.slots(date(2026, 11, 14))) == 28


def test_golden_vector_g1():
    now = pd.Timestamp("2026-11-14T23:30:00-05:00").tz_convert("UTC")
    r = pd.DataFrame({"ts": [now - pd.Timedelta(minutes=m) for m in (5, 12, 20, 40)], "scout_id": list("abcd"),
                      "crowd": [4, 4, 3, 4], "dancing": [2, 1, 1, 2], "line_minutes": [10, 15, 10, 5],
                      "cover_usd": [np.nan] * 4, "music_genre": [None] * 4, "verified_presence": [1] * 4,
                      "status": ["accepted"] * 4, "reputation": [0.8] * 4})
    s = _live_state.compute("v", r, None, now)
    assert s["vibe_score"] == 65 and abs(s["confidence"] - 0.67) <= 0.01
    assert s["crowd"] == 3.8 and s["dancing"] == 1.5 and s["line_minutes"] == 10 and s["n_reports"] == 4


def test_live_state_nulls_and_cutoff():
    now = pd.Timestamp("2026-11-14T23:30:00-05:00").tz_convert("UTC")
    old = pd.DataFrame({"ts": [now - pd.Timedelta(minutes=200), now + pd.Timedelta(minutes=5)],
                        "scout_id": ["a", "b"], "crowd": [3, 3], "dancing": [np.nan, np.nan],
                        "line_minutes": [np.nan, np.nan], "cover_usd": [np.nan] * 2, "music_genre": [None] * 2,
                        "verified_presence": [1, 1], "status": ["accepted"] * 2, "reputation": [0.5] * 2})
    s = _live_state.compute("v", old, None, now)
    assert s["vibe_score"] is None and s["confidence"] is None and s["n_reports"] == 0


def test_opening_hours_parser():
    assert night_window(parse_hours("Mo-Su 18:00-04:00"), 5) == (20.0, 27.0)
    assert night_window(parse_hours("Tu-We 17:00-01:00, Th 17:00-02:00, Fr 17:00-03:00"), 3) == (20.0, 26.0)
    assert night_window(parse_hours("Mo-Fr 17:00-24:00, Sa-Su 15:00-24:00"), 4) == (20.0, 24.0)
    assert night_window(parse_hours("Mo-We 18:00-02:00+;Th-Fr 18:00-03:00+"), 5) == (27.0, 27.0)  # closed Sat
    assert night_window(None, 4) == (20.0, 27.0)
