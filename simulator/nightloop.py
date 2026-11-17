"""Week-by-week, slot-by-slot night loop: scout visits -> raw reports, bounties, engagement & churn.

# SYNTHETIC: replace with real POST /api/reports traffic and the backend's bounty job.
Bounties (specs §7.5) change where Scouts go, so reports and bounties are generated in one loop.
A fast numpy copy of specs §5.6 confidence is used here (status-provisional, reputation 0.5).
"""
from __future__ import annotations

import heapq
import math
from collections import defaultdict
from datetime import date, timedelta

import numpy as np
import pandas as pd

from . import scouts as scouts_mod
from . import timeutil

CHIPS = np.array([0, 5, 10, 20, 30])


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km (vectorised)."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dl = np.radians(np.asarray(lon2) - np.asarray(lon1))
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def quick_conf(rows: list, now_min: float, sp: dict) -> tuple[float | None, int | None, float]:
    """(confidence, freshness_minutes, agree) from [(minute, scout, crowd, verified)] at venue (specs §5.6)."""
    if not rows:
        return None, None, 1.0
    a = np.array([(m, c, v) for m, _, c, v in rows], float)
    age = now_min - a[:, 0]
    ok = (age >= -sp["skew_minutes"]) & (age <= sp["cutoff_minutes"])
    if not ok.any():
        return None, None, 1.0
    age, a = np.clip(age[ok], 0, None), a[ok]
    w = (sp["w_rep_a"] + sp["w_rep_b"] * 0.5) * np.where(a[:, 2] == 1, 1.0, sp["w_unverified"])
    w = w * 0.5 ** (age / sp["half_life_crowd"])
    W = w.sum()
    mu = (w * a[:, 1]).sum() / W
    sd = math.sqrt(float((w * (a[:, 1] - mu) ** 2).sum() / W))
    agree = 1 - 0.5 * min(1.0, sd / 1.5)
    sc = {s for (m, s, _, _), k in zip(rows, ok) if k}
    conf = round((1 - math.exp(-W / sp["conf_k"])) * agree * (1.0 if len(sc) >= 2 else 0.6), 2)
    return conf, int(math.floor(age.min())), agree


class World:
    """Static per-run lookups for the loop."""

    def __init__(self, cfg, attrs, venues, truth, nights):
        self.cfg, self.sp, self.sc = cfg, cfg["specs"], cfg["scouts"]
        a = attrs.sort_values("venue_id").reset_index(drop=True)
        v = venues.set_index("venue_id").loc[a["venue_id"]]
        self.vid = a["venue_id"].to_numpy()
        self.vidx = {x: i for i, x in enumerate(self.vid)}
        self.lat, self.lon = v["lat"].to_numpy(float), v["lon"].to_numpy(float)
        self.dist = haversine_km(self.lat[:, None], self.lon[:, None], self.lat[None, :], self.lon[None, :])
        self.style = a["style"].to_numpy()
        self.genres = [g.split("|") for g in a["genres"]]
        self.truth = {}
        for d, g in truth.groupby("_night", sort=False):
            g = g.sort_values(["venue_id", "ts"])
            n_v = len(self.vid)
            self.truth[d] = {k: g[c].to_numpy().reshape(n_v, -1) for k, c in
                             [("crowd", "crowd_true"), ("dance", "dancing_true"), ("line", "line_minutes_true"),
                              ("cover", "cover_usd_true"), ("genre", "genre_true"), ("frac", "_frac"),
                              ("open", "_open")]}
        self.nights = nights


def _plan_visits(w: World, rng, s: dict, n_slots: int) -> list[tuple[float, str]]:
    """Arrival minutes (elapsed since 20:00) and kind ('visit' | 'burst') for one scout-night."""
    sc, end = w.sc, n_slots * 15 - 6
    if s["archetype"] == "gamer":
        out = []
        for _ in range(int(rng.integers(1, 3))):
            t = float(rng.uniform(30, end - 30))
            for _ in range(int(rng.integers(*sc["gamer_burst"]))):
                out.append((t, "burst"))
                t += float(rng.uniform(1, 4))
        return out
    n = int(rng.integers(sc["visits_per_night"][0], sc["visits_per_night"][1] + 1))
    t = float(np.clip(rng.normal(sc["arrival_mean_min"], sc["arrival_sd_min"]), 20, end - 20))
    out = []
    for _ in range(n):
        if t >= end:
            break
        out.append((t, "visit"))
        t += float(rng.uniform(*sc["stay_minutes"])) + float(rng.uniform(5, 15))
    return out


def _choose_venue(w: World, rng, s, slot, tr, bounties, visited) -> int | None:
    is_open = tr["open"][:, slot].astype(bool)
    if not is_open.any():
        return None
    if bounties and rng.random() < w.sc["bounty_redirect_p"] * s["engagement"]:
        best = max(bounties.items(), key=lambda kv: kv[1]["points"] / (1 + w.dist[kv[0]].mean()) + rng.random())
        if is_open[best[0]]:
            return best[0]
    if s["archetype"] == "shill" and rng.random() < w.sc["shill_home_p"]:
        h = w.vidx[s["home_venue_id"]]
        if is_open[h]:
            return h
    home_d = haversine_km(s["home_lat"], s["home_lon"], w.lat, w.lon)
    score = np.array([s["taste"][x] for x in w.style]) * (0.2 + tr["frac"][:, slot]) * np.exp(-home_d / 1.0)
    score = np.where(is_open & ~np.isin(np.arange(len(score)), list(visited)), score, 0)
    if score.sum() <= 0:
        return None
    return int(rng.choice(len(score), p=score / score.sum()))


def _observe(w: World, rng, s, vi, slot, tr) -> dict:
    sc, ob = w.sc, w.sc["obs"][s["archetype"]]
    sig, ns = s["true_accuracy"], ob["null_scale"]
    tc, td, tl = int(tr["crowd"][vi, slot]), int(tr["dance"][vi, slot]), int(tr["line"][vi, slot])
    home = s["archetype"] == "shill" and w.vid[vi] == s["home_venue_id"]
    if s["archetype"] == "gamer":
        crowd, dance, line = 5, 2, int(rng.choice(CHIPS))
    else:
        bias = ob["bias"] if home else 0.0
        crowd = int(np.clip(round(tc + bias + rng.normal(0, sig)), 1, 5))
        dance = int(np.clip(round(td + (1 if home else 0) + rng.normal(0, 0.5 * sig)), 0, 2))
        lv = max(0.0, tl + (15 if home else 0) + rng.normal(0, 3 + 5 * sig))
        line = int(CHIPS[np.abs(CHIPS - lv).argmin()])
    cover = tr["cover"][vi, slot]
    cover = None if (rng.random() < min(0.95, sc["cover_null_p"] * ns) or np.isnan(cover)) else int(cover)
    if cover is not None and s["archetype"] == "sloppy" and rng.random() < 0.3:
        cover = max(0, cover + int(rng.choice([-5, 5])))
    genre = tr["genre"][vi, slot] if rng.random() >= min(0.95, sc["genre_null_p"] * ns) else None
    if genre is not None and rng.random() < 0.15 * sig:
        genre = str(rng.choice(w.genres[int(rng.integers(len(w.genres)))]))
    if rng.random() < ob["presence_p"]:
        dist = int(rng.integers(0, w.sp["presence_radius_m"] + 1))
    else:
        dist = None if rng.random() < sc["gps_denied_p"] else int(rng.integers(*sc["far_distance_m"]))
    return {"crowd": crowd, "dancing": None if rng.random() < sc["dance_null_p"] * ns else dance,
            "line_minutes": None if rng.random() < sc["line_null_p"] * ns else line, "cover_usd": cover,
            "music_genre": genre, "distance_m": dist,
            "verified_presence": int(dist is not None and dist <= w.sp["presence_radius_m"])}


class NightState:
    """Mutable state for one night of the loop."""

    def __init__(self):
        self.by_venue = defaultdict(list)   # vi -> [(minute, scout, crowd, verified)]
        self.last_at = {}                    # (scout, vi) -> minute
        self.recent = defaultdict(list)      # scout -> [minutes]
        self.last_pos = {}                   # scout -> (minute, vi)
        self.bounties = {}                   # vi -> bounty dict (open)


def _night(w: World, rng, d: date, plans: dict, scouts: list, out: dict, week_stats: dict) -> None:
    sp = w.sp
    tr = w.truth[d]
    start, _ = timeutil.night_bounds(d)
    n_slots = tr["crowd"].shape[1]
    ns = NightState()
    heap = []
    for si, visits in plans.items():
        for t, kind in visits:
            heapq.heappush(heap, (t, si, kind, -1))
    visited = defaultdict(set)
    for slot in range(n_slots):
        lo, hi = slot * 15, slot * 15 + 15
        while heap and heap[0][0] < hi:
            t, si, kind, fixed = heapq.heappop(heap)
            s = scouts[si]
            vi = fixed if fixed >= 0 else (int(rng.integers(len(w.vid))) if kind == "burst" else
                                           _choose_venue(w, rng, s, slot, tr, ns.bounties, visited[si]))
            if vi is None or not tr["open"][vi, int(t // 15)]:
                continue
            visited[si].add(vi)
            if _report(w, rng, d, start, t, si, s, vi, tr, ns, out, week_stats) and kind == "visit" and fixed < 0:
                stay = float(rng.uniform(*w.sc["stay_minutes"]))
                if stay > 25 and rng.random() < w.sc["second_report_p"]:
                    t2 = t + float(rng.uniform(21, stay))
                    if t2 < n_slots * 15 - 1:
                        heapq.heappush(heap, (t2, si, "visit", vi))
        _bounty_check(w, d, start, hi, slot, tr, ns, out)
    for b in ns.bounties.values():
        out["bounties"].append(b)


def _report(w, rng, d, start, t, si, s, vi, tr, ns, out, week_stats) -> bool:
    sp = w.sp
    last = ns.last_at.get((si, vi))
    ns.recent[si] = [m for m in ns.recent[si] if m > t - 60]
    if (last is not None and t - last < sp["rate_per_venue_minutes"]) or len(ns.recent[si]) >= sp["rate_per_hour"]:
        out["stats"]["rate_limited_dropped"] += 1
        return False
    slot = int(t // 15)
    obs = _observe(w, rng, s, vi, slot, tr)
    vel = False
    if si in ns.last_pos:
        pm, pv = ns.last_pos[si]
        if pv != vi:
            dt_h = max(t - pm, 1e-6) / 60
            vel = w.dist[pv, vi] / dt_h > sp["velocity_kmh"]
    ns.last_at[(si, vi)] = t
    ns.recent[si].append(t)
    ns.last_pos[si] = (t, vi)
    ts = start + pd.Timedelta(seconds=round(t * 60))
    out["reports"].append({"venue_id": w.vid[vi], "scout_id": s["scout_id"], "ts": ts, **obs, "_night": d})
    st = week_stats[si]
    st["reports"] += 1
    if vel:
        st["flags"] += 1
        return True
    ns.by_venue[vi].append((t, s["scout_id"], obs["crowd"], obs["verified_presence"]))
    st["points"] += 10 + 5 * obs["verified_presence"]
    b = ns.bounties.get(vi)
    if b is not None and obs["verified_presence"] == 1:
        b["claimed_by"], b["claimed_at"] = s["scout_id"], ts
        out["bounties"].append(b)
        del ns.bounties[vi]
        st["points"] += b["points"]
        st["bounty_wins"] += 1
    return True


def _bounty_check(w, d, start, minute, slot, tr, ns, out) -> None:
    sp = w.sp
    t_utc = start + pd.Timedelta(minutes=minute)
    h = timeutil.local_hour(t_utc)
    for vi in [k for k, b in ns.bounties.items() if b["expires_at"] <= t_utc]:
        out["bounties"].append(ns.bounties.pop(vi))
    if not (sp["bounty_check_hours"][0] <= h <= sp["bounty_check_hours"][1]):
        return
    cand = []
    nxt = min(slot + 1, tr["open"].shape[1] - 1)
    for vi in range(len(w.vid)):
        if vi in ns.bounties or not tr["open"][vi, nxt]:
            continue
        conf, fresh, agree = quick_conf(ns.by_venue[vi], minute, sp)
        if conf is None or conf < sp["bounty_conf"]:
            cand.append((-1 if conf is None else conf, w.vid[vi], vi, fresh, agree))
    for conf, _, vi, fresh, agree in sorted(cand):
        if len(ns.bounties) >= sp["bounty_max_open"]:
            break
        pts = sp["bounty_null_points"] if fresh is None else sp["bounty_base"] + sp["bounty_step"] * min(3, fresh // 30)
        ns.bounties[vi] = {"venue_id": w.vid[vi], "created_at": t_utc, "points": int(pts),
                           "reason": "conflicting reports" if agree < sp["bounty_conflict_agree"] else
                           "no fresh reports", "claimed_by": None,
                           "expires_at": t_utc + pd.Timedelta(minutes=sp["bounty_expire_min"]), "claimed_at": None}


def run(cfg: dict, rng: np.random.Generator, attrs: pd.DataFrame, venues: pd.DataFrame, truth: pd.DataFrame,
        nights: list[date], scouts_rng: np.random.Generator) -> dict:
    """Returns {'reports', 'bounties', 'scouts' (population + churned_at), 'stats'}."""
    w = World(cfg, attrs, venues, truth, nights)
    sc = cfg["scouts"]
    weeks = sorted({d - timedelta(days=d.weekday() - 3) for d in timeutil.all_nights()})
    pop = scouts_mod.population(cfg, scouts_rng, attrs, weeks)
    scouts = pop.to_dict("records")
    for s in scouts:
        s.update(state="pending", churned_at=None, away=0, active_prev=False)
    out = {"reports": [], "bounties": [], "stats": {"rate_limited_dropped": 0}}
    sim_weeks = sorted({d - timedelta(days=d.weekday() - 3) for d in nights})
    for thu in sim_weeks:
        wk_nights = [d for d in nights if thu <= d < thu + timedelta(days=3)]
        week_end = timeutil.night_bounds(thu + timedelta(days=2))[1]
        start_thu = timeutil.night_bounds(thu)[0]
        week_stats = defaultdict(lambda: {"reports": 0, "points": 0, "bounty_wins": 0, "flags": 0})
        plans = {d: {} for d in wk_nights}
        for si, s in enumerate(scouts):
            if s["joined_at"] > start_thu:
                continue
            if s["state"] == "pending":
                s["state"] = "active"
            if s["state"] == "churned":
                s["away"] += 1
                if s["away"] >= sc["return_min_weeks"] and rng.random() < sc["return_p"]:
                    s.update(state="active", engagement=0.45, churned_at=None, away=0)
                else:
                    continue
            k = min(len(wk_nights), int(rng.poisson(sc["nights_per_week_rate"] * s["engagement"])))
            nw = np.array([sc["night_weight"][str(d.weekday())] for d in wk_nights])
            for j in sorted(rng.choice(len(wk_nights), size=k, replace=False, p=nw / nw.sum())) if k else []:
                d = wk_nights[j]
                plans[d][si] = _plan_visits(w, rng, s, w.truth[d]["crowd"].shape[1])
        for d in wk_nights:
            _night(w, rng, d, plans[d], scouts, out, week_stats)
        for si, s in enumerate(scouts):
            if s["state"] != "active":
                continue
            st = week_stats[si]
            active = st["reports"] > 0
            s["engagement"] = scouts_mod.update_engagement(cfg, rng, s["engagement"], st["points"],
                                                           st["bounty_wins"], active and s["active_prev"],
                                                           st["flags"])
            s["active_prev"] = active
            if s["engagement"] < sc["churn_threshold"]:
                s.update(state="churned", churned_at=week_end, away=0)
    pop = pd.DataFrame(scouts)
    return {"reports": pd.DataFrame(out["reports"]), "bounties": pd.DataFrame(out["bounties"], columns=[
        "venue_id", "created_at", "points", "reason", "claimed_by", "expires_at", "claimed_at"]),
            "scouts": pop, "stats": out["stats"]}
