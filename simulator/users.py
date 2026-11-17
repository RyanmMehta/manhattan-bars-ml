"""Synthetic app users with saved preferences -> syn_users (prefs_json = CONTRACTS Preferences block).

# SYNTHETIC: replace with real onboarding answers. Home points are coarse synthetic locations, not real people.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd


def generate(cfg: dict, rng: np.random.Generator) -> pd.DataFrame:
    uc = cfg["users"]
    mix = np.array(uc["home_mix"], float)
    names = cfg["scouts"]["names_a"], cfg["scouts"]["names_b"]
    pers = list(uc["personas"])
    pp = np.array([uc["personas"][k]["p"] for k in pers])
    rows = []
    for i in range(uc["n"]):
        c = mix[rng.choice(len(mix), p=mix[:, 3] / mix[:, 3].sum())]
        lat, lon = c[0] + rng.normal(0, c[2]), c[1] + rng.normal(0, c[2])
        p = uc["personas"][pers[rng.choice(len(pers), p=pp / pp.sum())]]
        k = int(rng.integers(1, 4))
        prefs = {"genres": sorted(rng.choice(p["genres"], size=min(k, len(p["genres"])), replace=False).tolist()),
                 "want_dancing": bool(p["want_dancing"]),
                 "crowd_pref": int(rng.integers(p["crowd_pref"][0], p["crowd_pref"][1] + 1)),
                 "max_cover_usd": int(rng.integers(p["max_cover"][0] // 5, p["max_cover"][1] // 5 + 1) * 5),
                 "max_line_minutes": int(rng.choice([5, 10, 15, 20, 30])),
                 "max_distance_km": float(rng.choice([0.5, 1.0, 1.5, 2.0, 3.0])),
                 "lat": round(float(lat), 4), "lon": round(float(lon), 4),
                 "group_size": int(rng.integers(1, 7))}
        rows.append({"user_id": f"syn-u-{i + 1:04d}",
                     "display_name": f"{rng.choice(names[0])} {rng.choice(names[1])} (user {i + 1})",
                     "home_lat": round(float(lat), 4), "home_lon": round(float(lon), 4),
                     "prefs_json": json.dumps(prefs, sort_keys=True), "is_synthetic": 1})
    return pd.DataFrame(rows)
