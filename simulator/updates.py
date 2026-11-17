"""Operator posts for claimed venues -> syn_venue_updates (cover, DJ, genres, event, offer + expiry).

# SYNTHETIC: replace with real posts from POST /api/owner/{venue_id}/updates.
Event nights also boost true crowd (truth.py reads the hidden `_event` flag).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from .config import GENRES
from .timeutil import TZ


def _local(d: date, hour: float) -> pd.Timestamp:
    t = datetime.combine(d, datetime.min.time(), tzinfo=TZ) + timedelta(hours=hour)
    return pd.Timestamp(t.replace(tzinfo=None)).tz_localize(TZ).tz_convert("UTC")


def generate(cfg: dict, rng: np.random.Generator, attrs: pd.DataFrame, nights: list[date]) -> pd.DataFrame:
    """One row per post; `_night` (date) kept as a hidden helper column."""
    uc = cfg["updates"]
    menu = cfg["venues"]["genre_menu"]
    rows = []
    claimed = attrs[attrs["is_claimed"] == 1].sort_values("venue_id")
    for d in nights:
        for _, v in claimed.iterrows():
            k = int(rng.choice(len(uc["per_night_p"]), p=uc["per_night_p"]))
            hours = np.sort(rng.uniform(*uc["post_hour_range"], size=k))
            for h in hours:
                ts = _local(d, float(h))
                cover = int(v["typical_cover_usd"])
                if rng.random() < uc["disagree_p"]:  # operator post disagrees with what Scouts will see
                    cover = max(0, cover + int(rng.choice([-10, -5, 5, 10])))
                dj = str(rng.choice(uc["djs"])) if rng.random() < uc["dj_p"] else None
                genres = v["genres"].split("|")
                if dj:
                    genres = sorted(set(genres) | {str(rng.choice(menu[v["style"]]))}, key=GENRES.index)
                event = str(rng.choice(uc["events"])) if rng.random() < uc["event_p"] else None
                offer, exp = None, None
                if rng.random() < uc["offer_p"]:
                    offer = str(rng.choice(uc["offers"]))
                    start = max(ts, _local(d, 20.0))
                    exp = start + pd.Timedelta(hours=float(rng.uniform(*uc["offer_hours"])))
                    exp = exp.floor("15min")
                rows.append({"venue_id": v["venue_id"], "ts": ts.floor("min"), "cover_usd": cover, "dj": dj,
                             "genres": "|".join(genres), "event": event, "offer": offer, "offer_expires_at": exp,
                             "is_synthetic": 1, "_night": d})
    cols = ["venue_id", "ts", "cover_usd", "dj", "genres", "event", "offer", "offer_expires_at", "is_synthetic",
            "_night"]
    df = pd.DataFrame(rows, columns=cols).sort_values(["ts", "venue_id"], kind="stable").reset_index(drop=True)
    df.insert(0, "update_id", [f"syn-up-{i + 1:05d}" for i in range(len(df))])
    return df
