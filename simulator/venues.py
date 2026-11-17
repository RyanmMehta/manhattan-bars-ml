"""Static venue attributes for the 35 launch venues -> syn_venue_attributes (+ hidden popularity).

# SYNTHETIC: style/genres/dance floor/cover/capacity/price/claimed are rule-based guesses about real,
# named bars; replace with data/venue_attributes_manual.csv (team-labelled) and claimed operator profiles.
opening_hours is real (OSM) when present.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from .config import GENRES, REPO

DAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
MANUAL = REPO / "data" / "venue_attributes_manual.csv"


def _style(row, rng, prior: dict) -> str:
    name, amen, cuisine = str(row["name"]).upper(), str(row["osm_amenity"]), str(row["cuisine"])
    if amen == "nightclub" or re.search(r"BALLROOM|\bCLUB\b|\bTHE BOX\b", name):
        return "club"
    if amen == "pub" or re.search(r"\bPUB\b|DONNYBROOK|KELTIC|HAIR OF THE DOG", name):
        return "pub"
    if re.search(r"COCKTAIL|\bROOM\b|CHAMPAGNE", name):
        return "cocktail"
    if "LOUNGE" in name:
        return "lounge"
    if re.search(r"WINE|CAFE|GROCERY|DISPENSARY|SKIN CONTACT", name):
        return "restaurant-bar" if "GROCERY" not in name else "dive"
    if cuisine not in ("American", "Other", "nan"):
        return "restaurant-bar"
    keys = list(prior)
    p = np.array([prior[k] for k in keys], float)
    return keys[rng.choice(len(keys), p=p / p.sum())]


def generate(cfg: dict, rng: np.random.Generator, inputs: pd.DataFrame) -> pd.DataFrame:
    """Return syn_venue_attributes plus a hidden `_popularity` column (dropped before writing)."""
    vc = cfg["venues"]
    rows = []
    for _, v in inputs.sort_values("venue_id").iterrows():
        style = _style(v, rng, vc["style_prior"])
        floor = int(rng.random() < vc["dance_floor_p"][style])
        lo, hi = vc["capacity"]["club" if style == "club" else "other"]
        cap = int(rng.integers(lo, hi + 1) // 5 * 5)
        cover = 0
        if style == "club" or floor:
            c0, c1 = vc["cover_range"]
            cover = int(rng.choice(np.arange(c0, c1 + 1, 5)))
        price = vc["price_base"][style] + (0 if v["liquor_tier"] == "full_liquor" else -1) + int(rng.random() < 0.3)
        menu = vc["genre_menu"][style]
        k = int(rng.integers(1, min(3, len(menu)) + 1))
        genres = sorted(rng.choice(menu, size=k, replace=False), key=GENRES.index)
        pop = float(np.exp(0.12 * np.log1p(v["noise_complaints"]) + rng.normal(0, vc["popularity_sigma"])))
        oh = v["opening_hours"] if isinstance(v["opening_hours"], str) and v["opening_hours"] else None
        rows.append({"venue_id": v["venue_id"], "genres": "|".join(genres), "style": style, "has_dance_floor": floor,
                     "typical_cover_usd": cover, "capacity": cap, "price_level": int(np.clip(price, 1, 4)),
                     "is_claimed": int(rng.random() < vc["claimed_p"]), "opening_hours": oh, "is_synthetic": 1,
                     "_popularity": pop})
    df = pd.DataFrame(rows)
    df["_popularity"] = df["_popularity"] / df["_popularity"].mean()
    return apply_manual(df)


def apply_manual(df: pd.DataFrame, path: Path = MANUAL) -> pd.DataFrame:
    """Team-labelled facts (data/venue_attributes_manual.csv, is_synthetic=0) drive the simulation when present.
    The written syn_ rows still carry is_synthetic=1; backend prefers the manual rows."""
    if not path.exists():
        return df
    man = pd.read_csv(path, dtype={"venue_id": str})
    cols = [c for c in man.columns if c in df.columns and c not in ("venue_id", "is_synthetic")]
    df = df.set_index("venue_id")
    for _, m in man.iterrows():
        if m["venue_id"] in df.index:
            for c in cols:
                if pd.notna(m[c]):
                    df.at[m["venue_id"], c] = m[c]
    return df.reset_index()


def _tmin(s: str) -> int:
    h, m = s.rstrip("+").split(":")
    return int(h) * 60 + int(m)


def _days(spec: str) -> set[int]:
    out: set[int] = set()
    for part in spec.replace(" ", "").split(","):
        if "-" in part:
            a, b = part.split("-")
            if a in DAYS and b in DAYS:
                i, j = DAYS.index(a), DAYS.index(b)
                out |= {k % 7 for k in range(i, j + 1 if j >= i else j + 8)}
        elif part in DAYS:
            out.add(DAYS.index(part))
    return out


def parse_hours(oh: str | None) -> dict[int, list[tuple[int, int]]] | None:
    """Very small OSM opening_hours parser -> {weekday: [(open_min, close_min)]} (close may exceed 1440).
    Returns None when unknown or unparseable (venue treated as open all night)."""
    if not oh or not isinstance(oh, str):
        return None
    rules = re.findall(r"((?:(?:Mo|Tu|We|Th|Fr|Sa|Su)(?:\s*-\s*(?:Mo|Tu|We|Th|Fr|Sa|Su))?\s*,?\s*)*)"
                       r"\s*((?:\d{1,2}:\d{2}-\d{1,2}:\d{2}\+?\s*,?\s*)+)", oh)
    out: dict[int, list[tuple[int, int]]] = {}
    for dspec, times in rules:
        days = _days(dspec.strip().rstrip(",")) if dspec.strip() else set(range(7))
        for t in re.findall(r"\d{1,2}:\d{2}-\d{1,2}:\d{2}\+?", times):
            a, b = t.split("-")
            o, c = _tmin(a), _tmin(b)
            if c <= o:
                c += 1440
            for d in days:
                out.setdefault(d, []).append((o, c))
    return out or None


def night_window(hours: dict | None, weekday: int) -> tuple[float, float]:
    """Open/close on the 20..27 local-hour scale for the night starting on `weekday` (Mon=0)."""
    if hours is None:
        return 20.0, 27.0
    opens, closes = [], []
    for o, c in hours.get(weekday, []):
        if c > 20 * 60:  # covers part of the evening
            opens.append(max(o, 20 * 60))
            closes.append(c)
    for o, c in hours.get((weekday + 1) % 7, []):  # after-midnight entries like "Fr 00:00-04:00"
        if o == 0:
            closes.append(1440 + c)
            if not opens:
                opens.append(24 * 60)
    if not closes:
        return 27.0, 27.0  # closed that night
    return max(20.0, min(opens) / 60), min(27.0, max(closes) / 60)
