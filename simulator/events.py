"""App usage events -> syn_venue_events (view|tap|save|recommend_impression), shaped by venue busyness.

# SYNTHETIC: replace with real frontend/backend event logging (venue_events table).
Fallback model (PRD §6): impressions per venue-slot ~ Poisson(rate x busyness), then a tap/save funnel.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def generate(cfg: dict, rng: np.random.Generator, truth: pd.DataFrame, users: pd.DataFrame,
             pop_by_venue: pd.Series) -> pd.DataFrame:
    ec = cfg["events"]
    t = truth[["venue_id", "ts", "_frac"]].reset_index(drop=True)
    n_nights = max(1, truth["_night"].nunique())
    busy = (0.3 + t["_frac"].to_numpy()) * t["venue_id"].map(pop_by_venue).to_numpy()
    mean_imp = ec["sessions_per_night"] * np.mean(ec["impressions_per_session"]) * n_nights
    lam = busy / busy.sum() * mean_imp
    total_est = mean_imp * (1 + ec["tap_p"] * (1 + ec["view_per_tap"] + ec["save_p"]))
    lam *= min(1.0, ec["max_rows"] / total_est)
    imp = rng.poisson(lam)
    tap = rng.binomial(imp, ec["tap_p"])
    view = rng.binomial(tap, min(1.0, ec["view_per_tap"]))
    save = rng.binomial(tap, ec["save_p"])
    parts = []
    for kind, n in (("recommend_impression", imp), ("tap", tap), ("view", view), ("save", save)):
        idx = np.repeat(np.arange(len(t)), n)
        parts.append(pd.DataFrame({"venue_id": t["venue_id"].to_numpy()[idx], "_slot": t["ts"].to_numpy()[idx],
                                   "event_type": kind}))
    df = pd.concat(parts, ignore_index=True)
    df["ts"] = pd.to_datetime(df["_slot"], utc=True) + pd.to_timedelta(rng.integers(0, 900, len(df)), unit="s")
    uid = users["user_id"].to_numpy()
    anon = rng.random(len(df)) < ec["anon_p"]
    df["user_id"] = np.where(anon, None, uid[rng.integers(0, len(uid), len(df))])
    df = df.sort_values(["ts", "venue_id", "event_type"], kind="stable").reset_index(drop=True)
    df.insert(0, "event_id", [f"syn-e-{i + 1:07d}" for i in range(len(df))])
    df["is_synthetic"] = 1
    return df[["event_id", "venue_id", "ts", "event_type", "user_id", "is_synthetic"]]
