"""Hidden true venue state per 15-min slot -> syn_true_state (EVALUATION ONLY; the app never reads it).

# SYNTHETIC: replace with proxies once real (door counts, verified check-ins); drop when real reports exist.
occupancy_frac = curve_style(hour) x weekday x night shock x venue-night shock x popularity x holiday x event,
with AR(1) noise between slots; 0 when closed per OSM opening_hours.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from . import timeutil
from .venues import night_window, parse_hours


def generate(cfg: dict, rng: np.random.Generator, attrs: pd.DataFrame, updates: pd.DataFrame,
             nights: list[date]) -> pd.DataFrame:
    """Rows per venue x slot; hidden helper columns `_frac`, `_night`, `_hour`, `_open` are dropped on write."""
    tc = cfg["truth"]
    a = attrs.sort_values("venue_id").reset_index(drop=True)
    hours = [parse_hours(x) for x in a["opening_hours"]]
    peak = a["style"].map(tc["style_peak_hour"]).to_numpy(float)[:, None]
    width = a["style"].map(tc["style_peak_width"]).to_numpy(float)[:, None]
    level = a["style"].map(tc["style_peak_level"]).to_numpy(float)[:, None]
    pop = a["_popularity"].to_numpy(float)[:, None]
    cap = a["capacity"].to_numpy(float)[:, None]
    floor = a["has_dance_floor"].to_numpy(int)[:, None]
    ev = updates[updates["event"].notna()][["venue_id", "_night"]]
    ev_set = set(zip(ev["venue_id"], ev["_night"]))
    out = []
    for d in nights:
        ts = timeutil.slots(d)
        h = timeutil.local_hour(ts)[None, :]
        n_v, n_s = len(a), len(ts)
        curve = tc["base_level"] + level * np.exp(-0.5 * ((h - peak) / width) ** 2)
        shock = np.exp(rng.normal(0, tc["night_sigma"]) + rng.normal(0, tc["venue_night_sigma"], (n_v, 1)))
        hol = tc["holidays"].get(d.isoformat(), 1.0)
        evb = np.array([tc["event_boost"] if (v, d) in ev_set else 1.0 for v in a["venue_id"]])[:, None]
        eps = np.zeros((n_v, n_s))
        z = rng.normal(0, tc["ar1_sigma"], (n_v, n_s))
        for j in range(n_s):
            eps[:, j] = (tc["ar1_rho"] * eps[:, j - 1] if j else 0) + z[:, j]
        frac = curve * tc["weekday"][str(d.weekday())] * shock * pop * hol * evb * np.exp(eps)
        win = np.array([night_window(hh, d.weekday()) for hh in hours])
        is_open = (h >= win[:, :1]) & (h < win[:, 1:])
        frac = np.clip(np.where(is_open, frac, 0.0), 0, 1.15)
        out.append(_to_frame(cfg, rng, a, d, ts, h, frac, is_open, cap, floor, ev_set))
    return pd.concat(out, ignore_index=True)


def _to_frame(cfg, rng, a, d, ts, h, frac, is_open, cap, floor, ev_set) -> pd.DataFrame:
    tc = cfg["truth"]
    n_v, n_s = frac.shape
    crowd = 1 + np.digitize(frac, tc["crowd_bins"])
    late = h >= tc["dance_min_hour"]
    dance_floor = np.where(late, np.digitize(frac, tc["dance_bins_floor"]), 0)
    dance_none = ((frac > 0.7) & (h >= tc["dance_min_hour"] + 1) &
                  (rng.random((n_v, n_s)) < tc["dance_no_floor_p"] * 4)).astype(int)
    dancing = np.where(floor == 1, dance_floor, dance_none)
    thr = tc["line_threshold"]
    line = np.where(frac > thr, np.round((frac - thr) / (1.15 - thr) * tc["line_max_minutes"]), 0).astype(int)
    evn = np.array([(v, d) in ev_set for v in a["venue_id"]])[:, None]
    cov = a["typical_cover_usd"].to_numpy(float)[:, None]
    cover = np.where((h >= tc["cover_from_hour"]) | evn, cov, 0.0) * np.ones((1, n_s))
    g_lists = [g.split("|") for g in a["genres"]]
    genre = np.empty((n_v, n_s), dtype=object)
    for i, gl in enumerate(g_lists):  # genre rotates every ~hour among the venue's genres
        start = int(rng.integers(len(gl)))
        genre[i] = [gl[(start + int(k // 4)) % len(gl)] for k in range(n_s)]
    return pd.DataFrame({
        "venue_id": np.repeat(a["venue_id"].to_numpy(), n_s), "ts": pd.DatetimeIndex(np.tile(ts.tz_convert(None).to_numpy(), n_v)).tz_localize("UTC"),
        "crowd_true": np.where(is_open, crowd, 1).ravel(), "dancing_true": np.where(is_open, dancing, 0).ravel(),
        "line_minutes_true": np.where(is_open, line, 0).ravel(),
        "cover_usd_true": np.where(is_open, cover, np.nan).ravel(),
        "genre_true": np.where(is_open, genre, None).ravel(),
        "occupancy": np.round(frac * cap).astype(int).ravel(), "is_synthetic": 1,
        "_frac": frac.ravel(), "_night": d, "_hour": np.tile(h.ravel(), n_v), "_open": is_open.ravel()})
