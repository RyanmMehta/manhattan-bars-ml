"""Post-visit outcomes -> syn_feedback, from a placeholder chooser over the TRUE state.

# SYNTHETIC: placeholder recommender + outcome model; replace with POST /api/feedback from real users
# (later: use recs.scoring.recommend as the chooser, OUTLINE L2).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .nightloop import haversine_km


def fit_score(prefs: dict, crowd, dancing, line, cover, genre, style_genres, dist_km) -> np.ndarray:
    """0-1 fit of each venue's true state to a user's prefs (vectorised over venues)."""
    g = np.array([1.0 if (gg in prefs["genres"]) else (0.5 if any(x in prefs["genres"] for x in sg) else 0.0)
                  for gg, sg in zip(genre, style_genres)])
    c = 1 - np.abs(crowd - prefs["crowd_pref"]) / 4
    d = (dancing / 2) if prefs["want_dancing"] else (1 - dancing / 2)
    ln = np.where(line <= prefs["max_line_minutes"], 1.0, 0.3)
    cv = np.where(np.nan_to_num(cover) <= prefs["max_cover_usd"], 1.0, 0.3)
    di = np.clip(1 - dist_km / max(prefs["max_distance_km"], 0.5) / 2, 0, 1)
    return 0.3 * g + 0.25 * c + 0.15 * d + 0.1 * ln + 0.1 * cv + 0.1 * di


def generate(cfg: dict, rng: np.random.Generator, truth: pd.DataFrame, users: pd.DataFrame,
             venues: pd.DataFrame, attrs: pd.DataFrame) -> pd.DataFrame:
    fc = cfg["feedback"]
    a = attrs.sort_values("venue_id").reset_index(drop=True)
    v = venues.set_index("venue_id").loc[a["venue_id"]]
    sg = [x.split("|") for x in a["genres"]]
    prefs = [json.loads(p) for p in users["prefs_json"]]
    rows = []
    for d, g in truth.groupby("_night", sort=True):
        slots = np.sort(g["ts"].unique())
        for ui in rng.choice(len(users), size=min(fc["per_night"], len(users)), replace=False):
            ts = slots[int(rng.integers(2, max(3, len(slots) - 8)))]
            s = g[(g["ts"] == ts)].set_index("venue_id").loc[a["venue_id"]]
            p = prefs[ui]
            dist = haversine_km(p["lat"], p["lon"], v["lat"].to_numpy(), v["lon"].to_numpy())
            f = fit_score(p, s["crowd_true"].to_numpy(float), s["dancing_true"].to_numpy(float),
                          s["line_minutes_true"].to_numpy(float), s["cover_usd_true"].to_numpy(float),
                          s["genre_true"].to_numpy(), sg, dist)
            f = np.where(s["_open"].to_numpy(), f, -1)
            top = np.argsort(-(f + rng.normal(0, fc["fit_noise"], len(f))), kind="stable")[: fc["top_k"]]
            vi = int(rng.choice(top))
            visited = int(rng.random() < fc["visited_p"])
            rating = int(np.clip(round(1 + 4 * f[vi] + rng.normal(0, fc["rating_noise"])), 1, 5)) if visited else None
            rows.append({"user_id": users["user_id"].iat[ui], "venue_id": a["venue_id"].iat[vi],
                         "recommended_at": pd.Timestamp(ts) + pd.Timedelta(minutes=int(rng.integers(0, 15))),
                         "visited": visited, "rating": rating, "is_synthetic": 1, "_fit": float(f[vi])})
    df = pd.DataFrame(rows).sort_values(["recommended_at", "user_id"], kind="stable").reset_index(drop=True)
    df.insert(0, "feedback_id", [f"syn-f-{i + 1:05d}" for i in range(len(df))])
    df["rating"] = df["rating"].astype("Int64")
    return df
