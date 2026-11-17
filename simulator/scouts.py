"""Scout population: weekly cohorts, archetypes, accuracy, taste and latent engagement.

# SYNTHETIC: replace with real Scout accounts (backend scouts table) and their real activity.
The latent engagement process (decay, bumps, churn threshold, returns) is advanced week by week
inside nightloop.py; this module creates the population and the engagement update rule.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from .timeutil import TZ


def population(cfg: dict, rng: np.random.Generator, attrs: pd.DataFrame, weeks: list[date]) -> pd.DataFrame:
    """One row per scout ever joining. `weeks` = Thursday of each simulated week (cohort 1 = first week)."""
    sc = cfg["scouts"]
    arche = list(sc["archetype_share"])
    p = np.array([sc["archetype_share"][k] for k in arche])
    styles = sorted(cfg["venues"]["style_prior"])
    rows, n = [], 0
    for wi, thu in enumerate(weeks):
        k = sc["week1"] if wi == 0 else int(rng.integers(sc["per_week"][0], sc["per_week"][1] + 1))
        for _ in range(k):
            n += 1
            a = str(arche[rng.choice(len(arche), p=p)])
            ob = sc["obs"][a]
            join = pd.Timestamp(f"{(thu - timedelta(days=int(rng.integers(0, 4)))).isoformat()} 12:00", tz=TZ)
            join = (join + pd.Timedelta(minutes=int(rng.integers(0, 8 * 60)))).tz_convert("UTC")
            taste = rng.dirichlet(np.ones(len(styles)) * 1.5)
            rows.append({"scout_id": f"syn-s-{n:04d}",
                         "display_name": f"{rng.choice(sc['names_a'])} {rng.choice(sc['names_b'])} {n:03d}",
                         "joined_at": join, "archetype": a, "cohort_week": wi + 1,
                         "home_venue_id": str(rng.choice(attrs["venue_id"])) if a == "shill" else None,
                         "true_accuracy": round(float(ob["sigma"] * rng.uniform(0.85, 1.15)), 3),
                         "engagement": float(rng.beta(*sc["engagement_beta"])),
                         "taste": dict(zip(styles, taste)), "home_lat": 40.7203 + rng.normal(0, 0.006),
                         "home_lon": -73.9881 + rng.normal(0, 0.006)})
    return pd.DataFrame(rows)


def update_engagement(cfg: dict, rng: np.random.Generator, e: float, week_points: float, bounty_wins: int,
                      streak: bool, flags: int) -> float:
    """Weekly latent engagement update (v2 §B): decay + bumps from points, bounty wins, streaks; flags hurt."""
    sc = cfg["scouts"]
    bump = (sc["bump_per_50_points"] * (week_points / 50) + sc["bump_bounty"] * bounty_wins
            + sc["bump_streak"] * streak - sc["penalty_flag"] * flags)
    return float(np.clip(sc["engagement_decay"] * e + sc["engagement_floor"] * (1 - sc["engagement_decay"])
                         + min(bump, sc["bump_cap"]) + rng.normal(0, 0.04), 0, 1))
