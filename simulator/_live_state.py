"""Minimal mirror of specs §5.1-5.7 (vibe, confidence, freshness, n_reports, trend).

# SYNTHETIC: mirror of specs §5; delete when recs.live_state is importable (it is preferred when present).
Used only to decide when bounties appear (specs §7.5) and to fill demo_night_snapshots.csv.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

SPEC = {"half_life_crowd": 30, "half_life_scout_cover_genre": 60, "half_life_operator": 120, "cutoff_minutes": 180,
        "skew_minutes": 2, "w_rep_a": 0.25, "w_rep_b": 0.75, "w_unverified": 0.6, "w_disputed": 0.5,
        "w_operator": 0.8, "conf_k": 1.5, "min_field_weight": 0.30, "genre_share": 0.30,
        "vibe_weights": {"crowd": 0.50, "dance": 0.35, "line": 0.15}}
STATUS_W = {"accepted": 1.0, "pending": 1.0, "disputed": 0.5, "flagged": 0.0, "removed": 0.0}


def _wmedian(x: np.ndarray, w: np.ndarray) -> float:
    o = np.argsort(x, kind="stable")
    x, w = x[o], w[o]
    c = np.cumsum(w)
    return float(x[np.searchsorted(c, 0.5 * c[-1])])


def _wmean(x, w):
    return float(np.sum(x * w) / np.sum(w))


def _field(x: np.ndarray, w: np.ndarray, sp: dict):
    m = ~np.isnan(x)
    return (x[m], w[m]) if m.any() and w[m].sum() >= sp["min_field_weight"] else (None, None)


def compute(venue_id: str, reports: pd.DataFrame, updates: pd.DataFrame | None, now: pd.Timestamp,
            spec: dict | None = None) -> dict:
    """Live Venue State for one venue from its scout reports (cols: ts UTC, scout_id, crowd, dancing,
    line_minutes, cover_usd, music_genre, verified_presence, status, reputation) and operator updates."""
    sp = {**SPEC, **(spec or {})}
    st = {"venue_id": venue_id, "crowd": None, "dancing": None, "line_minutes": None, "cover_usd": None,
          "music_genres": None, "vibe_score": None, "confidence": None, "freshness_minutes": None,
          "n_reports": 0, "trend": None, "sources": [], "is_synthetic": True}
    r = reports
    if r is not None and len(r):
        age = (now - r["ts"]).dt.total_seconds().to_numpy() / 60
        keep = (age >= -sp["skew_minutes"]) & (age <= sp["cutoff_minutes"])
        r, age = r[keep], np.clip(age[keep], 0, None)
    if r is None or not len(r):
        return st
    rep = r["reputation"].fillna(0.5).to_numpy(float) if "reputation" in r else np.full(len(r), 0.5)
    w_base = (sp["w_rep_a"] + sp["w_rep_b"] * rep) * np.where(r["verified_presence"].to_numpy() == 1, 1.0,
                                                               sp["w_unverified"])
    w_base = w_base * r["status"].map(STATUS_W).fillna(1.0).to_numpy(float) if "status" in r else w_base
    w_fast = w_base * 0.5 ** (age / sp["half_life_crowd"])
    w_slow = w_base * 0.5 ** (age / sp["half_life_scout_cover_genre"])
    pos = w_fast > 0
    if not pos.any():
        return st
    st["n_reports"] = int(pos.sum())
    st["freshness_minutes"] = int(math.floor(age[pos].min()))
    st["sources"] = ["scout"]
    crowd = r["crowd"].to_numpy(float)
    cx, cw = _field(crowd, w_fast, sp)
    dx, dw = _field(r["dancing"].to_numpy(float), w_fast, sp)
    lx, lw = _field(r["line_minutes"].to_numpy(float), w_fast, sp)
    vx, vw = _field(r["cover_usd"].to_numpy(float), w_slow, sp)
    if cx is not None:
        st["crowd"] = round(_wmean(cx, cw), 1)
    if dx is not None:
        st["dancing"] = round(_wmean(dx, dw), 1)
    if lx is not None:
        st["line_minutes"] = int(_wmedian(lx, lw))
    if vx is not None:
        st["cover_usd"] = int(_wmedian(vx, vw))
    g = r["music_genre"].to_numpy(object)
    gm = pd.notna(g)
    if gm.any() and w_slow[gm].sum() >= sp["min_field_weight"]:
        shares = pd.Series(w_slow[gm]).groupby(pd.Series(g[gm])).sum() / w_slow[gm].sum()
        shares = shares[shares >= sp["genre_share"]].sort_values(ascending=False, kind="stable")
        st["music_genres"] = list(shares.index)
    if cx is not None:
        raw = {"crowd": _wmean(cx, cw), "dance": _wmean(dx, dw) if dx is not None else None}
        _vibe_conf(st, raw, crowd, w_fast, r["scout_id"].to_numpy(), sp)
        st["trend"] = _trend(crowd, w_base, age, sp)
    elif (~np.isnan(crowd) & (w_fast > 0)).any():  # crowd too thin to state, but confidence still counts it (§5.6)
        _conf_only(st, crowd, w_fast, r["scout_id"].to_numpy(), sp)
    return st


def _conf_only(st: dict, crowd, w, scouts, sp) -> None:
    x, ww = _nn(crowd, w)
    W = ww.sum()
    mu = _wmean(x, ww)
    sd = math.sqrt(float(np.sum(ww * (x - mu) ** 2) / W))
    agree = 1 - 0.5 * min(1.0, sd / 1.5)
    diverse = 1.0 if len(set(scouts[~np.isnan(crowd) & (w > 0)])) >= 2 else 0.6
    st["confidence"] = round((1 - math.exp(-W / sp["conf_k"])) * agree * diverse, 2)


def _vibe_conf(st: dict, raw: dict, crowd, w, scouts, sp) -> None:
    a = sp["vibe_weights"]
    terms = [(a["crowd"], (raw["crowd"] - 1) / 4)]
    if raw["dance"] is not None:
        terms.append((a["dance"], raw["dance"] / 2))
    if st["line_minutes"] is not None:
        terms.append((a["line"], min(st["line_minutes"], 30) / 30))
    st["vibe_score"] = int(round(100 * sum(k * x for k, x in terms) / sum(k for k, _ in terms)))
    x, ww = _nn(crowd, w)
    W = ww.sum()
    support = 1 - math.exp(-W / sp["conf_k"])
    mu = _wmean(x, ww)
    sd = math.sqrt(float(np.sum(ww * (x - mu) ** 2) / W))
    agree = 1 - 0.5 * min(1.0, sd / 1.5)
    m = ~np.isnan(crowd) & (w > 0)
    diverse = 1.0 if len(set(scouts[m])) >= 2 else 0.6
    st["confidence"] = round(support * agree * diverse, 2)
    st["agree"] = round(agree, 3)


def _nn(x, w):
    m = ~np.isnan(x) & (w > 0)
    return x[m], w[m]


def _trend(crowd, w_base, age, sp):
    out = []
    for lo, hi in ((0, 30), (30, 90)):
        m = (age >= lo) & ((age <= hi) if lo == 0 else (age < hi)) & ~np.isnan(crowd)
        w = w_base[m] * 0.5 ** (age[m] / sp["half_life_crowd"])
        if w.sum() < 0.5:
            return None
        out.append(_wmean(crowd[m], w))
    d = out[0] - out[1]
    return "rising" if d >= 0.4 else "falling" if d <= -0.4 else "steady"
