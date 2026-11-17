"""SYNTHETIC interim generator: stand-in for live-sim's data/live_sim.db while it is not on origin.

# SYNTHETIC: replaced by data/live_sim.db (live-sim, `python -I -m simulator --seed 42 --out data/live_sim.db`),
#            then by real app tables. Swap: build live_sim.db; recs.data.live_tables("auto") picks it up.

Same table names/columns as CONTRACTS §E. Thu-Sat nights Aug 27 -> Nov 14 2026, 20:00-03:00 ET, seed 42.
Process (all made up, structure only):
- true crowd(venue, t) = 1 + 3.2·exp(-((h - peak_style)/2)^2) + popularity_v + weekday effect + night noise
- reports arrive Poisson per 15-min slot, rate ∝ true crowd; scouts by archetype (honest/casual/sloppy/gamer/shill)
  add bias/noise; reputation moves nightly towards each scout's observed accuracy (history kept per night).
- ~40% of venues are claimed and post one operator update per night (cover/genres/dj, sometimes an offer).
Results only measure this generator's structure, not real nightlife.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd

from ..config import GENRES, SEED, TZ

START, END = date(2026, 8, 27), date(2026, 11, 14)
STYLES = ["dive", "cocktail", "club", "lounge", "pub", "restaurant-bar"]
PEAK_H = {"club": 4.75, "dive": 3.0, "cocktail": 2.0, "lounge": 3.5, "pub": 2.5, "restaurant-bar": 1.5}  # hours after 20:00
DAY_EFFECT = {3: -0.5, 4: 0.0, 5: 0.3}  # Thu, Fri, Sat
ARCH = {  # share, crowd noise sd, bias, verified prob, nightly activity prob
    "honest": (0.45, 0.45, 0.0, 0.9, 0.55),
    "casual": (0.30, 0.75, 0.0, 0.75, 0.30),
    "sloppy": (0.12, 1.30, 0.0, 0.5, 0.35),
    "gamer": (0.08, 0.6, 1.0, 0.7, 0.6),
    "shill": (0.05, 0.5, 1.5, 0.6, 0.7),
}
N_SCOUTS = 150
SLOTS = 28  # 15-min slots 20:00 -> 03:00


def nights() -> list[date]:
    out, d = [], START
    while d <= END:
        if d.weekday() in DAY_EFFECT:
            out.append(d)
        d += timedelta(days=1)
    return out


def _ts(d: date, slot_min: float) -> datetime:
    return datetime.combine(d, time(20, 0), tzinfo=TZ) + timedelta(minutes=float(slot_min))


def _fix_tz(dt: datetime) -> datetime:
    return dt.astimezone(TZ)  # correct EDT/EST offset after adding minutes


def generate(launch: pd.DataFrame, seed: int = SEED) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    vids = list(launch["venue_id"])
    nv = len(vids)
    ns = nights()

    # --- venue attributes (SYNTHETIC: data/venue_attributes_manual.csv / claimed profiles) ---------------
    style = rng.choice(STYLES, size=nv, p=[0.25, 0.25, 0.1, 0.15, 0.15, 0.1])
    dance = np.where(style == "club", 1, (rng.random(nv) < 0.15).astype(int))
    cap = rng.integers(40, 260, size=nv)
    price = rng.integers(1, 5, size=nv)
    cover = np.where(style == "club", rng.choice([10, 15, 20, 25], size=nv), np.where(rng.random(nv) < 0.2, 10, 0))
    gen = [rng.choice(GENRES, size=2, replace=False) for _ in range(nv)]
    claimed = (rng.random(nv) < 0.4).astype(int)
    attrs = pd.DataFrame({
        "venue_id": vids, "genres": ["|".join(g) for g in gen], "style": style, "has_dance_floor": dance,
        "typical_cover_usd": cover, "capacity": cap, "price_level": price, "is_claimed": claimed,
        "opening_hours": None, "is_synthetic": 1,
    })
    pop = rng.uniform(-0.6, 0.6, size=nv)

    # --- scouts ----------------------------------------------------------------------------------------
    names = list(ARCH)
    arch = rng.choice(names, size=N_SCOUTS, p=[ARCH[a][0] for a in names])
    join_night = np.minimum(rng.geometric(0.08, size=N_SCOUTS) - 1, len(ns) - 4)
    home = rng.integers(0, nv, size=N_SCOUTS)
    churn_p = np.where(arch == "casual", 0.05, 0.025)
    rep = np.full(N_SCOUTS, 0.5)
    points = np.zeros(N_SCOUTS, dtype=int)
    n_rep = np.zeros(N_SCOUTS, dtype=int)
    churned = np.full(N_SCOUTS, -1)
    last_active = [None] * N_SCOUTS
    sid = [f"syn-s-{i + 1:04d}" for i in range(N_SCOUTS)]

    reports, truth, history, updates = [], [], [], []
    rid = 0
    uid = 0
    for k, d in enumerate(ns):
        wd = d.weekday()
        active = (join_night <= k) & (churned < 0)
        for i in np.where(active)[0]:
            history.append((sid[i], d.isoformat(), round(float(rep[i]), 4), int(points[i]), int(1 + points[i] // 100), 1))
        night_noise = rng.normal(0, 0.3, size=nv)
        act_today = active & (rng.random(N_SCOUTS) < np.array([ARCH[a][4] for a in arch]))
        pool = np.where(act_today)[0]
        err_sum = np.zeros(N_SCOUTS)
        err_n = np.zeros(N_SCOUTS)
        for v in range(nv):
            h = np.arange(SLOTS) * 0.25
            ct = 1 + 3.2 * np.exp(-((h - PEAK_H[style[v]]) / 2.0) ** 2) + pop[v] + DAY_EFFECT[wd] + 0.01 * k
            ct = np.clip(ct + night_noise[v] + rng.normal(0, 0.15, size=SLOTS), 1, 5)
            dt_ = np.clip((ct - 2) / 1.5, 0, 2) if dance[v] else np.clip((ct - 3.5) / 2, 0, 0.6)
            lt = np.maximum(0, np.round((ct - 3.6) * 15 * (150 / cap[v]) ** 0.5)).astype(int)
            cov = np.where(h >= 2, cover[v] + (5 if (wd == 5 and cover[v] > 0) else 0), 0)
            g_true = gen[v][0] if rng.random() < 0.7 else gen[v][1]
            for s in range(SLOTS):
                t = _fix_tz(_ts(d, s * 15))
                truth.append((vids[v], t.isoformat(), round(float(ct[s]), 2), round(float(dt_[s]), 2), int(lt[s]),
                              int(cov[s]), g_true, round(float(ct[s] / 5 * cap[v])), 1))
                lam = 0.30 * ct[s] / 3
                for _ in range(rng.poisson(lam)):
                    if len(pool) == 0:
                        break
                    # home-venue scouts (gamers/shills) favour their venue
                    homers = pool[(home[pool] == v) & np.isin(arch[pool], ["gamer", "shill"])]
                    i = int(rng.choice(homers)) if len(homers) and rng.random() < 0.5 else int(rng.choice(pool))
                    a = arch[i]
                    _, sd, bias, pver, _ = ARCH[a]
                    b = bias if home[i] == v else 0.0
                    c_rep = int(np.clip(np.rint(ct[s] + b + rng.normal(0, sd)), 1, 5))
                    err_sum[i] += abs(c_rep - ct[s])
                    err_n[i] += 1
                    dn = int(np.clip(np.rint(dt_[s] + rng.normal(0, sd / 2)), 0, 2)) if rng.random() < 0.85 else None
                    ln = int(5 * round(max(0, lt[s] * (1 + rng.normal(0, 0.3))) / 5)) if rng.random() < 0.8 else None
                    cv = int(cov[s]) if rng.random() < 0.3 else None
                    gg = (g_true if rng.random() < 0.8 else str(rng.choice(GENRES))) if rng.random() < 0.5 else None
                    ver = int(rng.random() < pver)
                    status = "accepted"
                    u = rng.random()
                    if a == "shill" and home[i] == v and u < 0.25:
                        status = "flagged"
                    elif u < 0.02:
                        status = "disputed"
                    when = _fix_tz(t + timedelta(minutes=float(rng.uniform(0, 15))))
                    rid += 1
                    reports.append((f"syn-r-{rid:06d}", vids[v], sid[i], when.isoformat(timespec="seconds"), c_rep, dn,
                                    ln, cv, gg, ver, status, int(rng.integers(5, 140)) if ver else None, 1))
                    n_rep[i] += 1
                    points[i] += 10 if ver else 5
                    last_active[i] = when.isoformat(timespec="seconds")
            if claimed[v] and rng.random() < 0.8:
                t = _fix_tz(_ts(d, float(rng.uniform(0, 120))))
                uid += 1
                offer = "2-for-1 well drinks" if rng.random() < 0.3 else None
                updates.append((f"syn-u-{uid:06d}", vids[v], t.isoformat(timespec="seconds"),
                                int(cover[v] + (5 if wd == 5 and cover[v] else 0)), f"DJ Syn{v:02d}" if dance[v] else None,
                                "|".join(gen[v]), None, offer,
                                _fix_tz(t + timedelta(hours=2)).isoformat(timespec="seconds") if offer else None, 1))
        # nightly reputation update towards accuracy (1 - mean abs error / 2)
        m = err_n > 0
        acc = np.clip(1 - err_sum[m] / err_n[m] / 2, 0, 1)
        rep[m] = rep[m] + 0.15 * (acc - rep[m])
        # churn
        ch = active & (rng.random(N_SCOUTS) < churn_p)
        churned[ch] = k

    cols_r = ["report_id", "venue_id", "scout_id", "ts", "crowd", "dancing", "line_minutes", "cover_usd", "music_genre",
              "verified_presence", "status", "distance_m", "is_synthetic"]
    r = pd.DataFrame(reports, columns=cols_r)
    for c in ("dancing", "line_minutes", "cover_usd", "distance_m"):
        r[c] = r[c].astype("Int64")
    scouts = pd.DataFrame({
        "scout_id": sid, "display_name": [f"Syn Scout {i + 1}" for i in range(N_SCOUTS)],
        "joined_at": [_ts(ns[j], 0).isoformat() for j in join_night], "reputation": np.round(rep, 4),
        "points": points, "level": 1 + points // 100, "reports_count": n_rep, "last_active_at": last_active,
        "is_synthetic": 1,
    })
    scout_truth = pd.DataFrame({
        "scout_id": sid, "archetype": arch, "home_venue_id": [vids[h] for h in home],
        "true_accuracy": [1 - ARCH[a][1] / 2 for a in arch], "cohort_week": join_night // 3,
        "churned_at": [ns[c].isoformat() if c >= 0 else None for c in churned], "is_synthetic": 1,
    })
    return {
        "syn_venue_attributes": attrs,
        "syn_scouts": scouts,
        "syn_scout_reports": r,
        "syn_venue_updates": pd.DataFrame(updates, columns=["update_id", "venue_id", "ts", "cover_usd", "dj", "genres", "event",
                                                            "offer", "offer_expires_at", "is_synthetic"]),
        "syn_scout_reputation_history": pd.DataFrame(history, columns=["scout_id", "as_of_date", "reputation", "points",
                                                                       "level", "is_synthetic"]),
        "syn_true_state": pd.DataFrame(truth, columns=["venue_id", "ts", "crowd_true", "dancing_true", "line_minutes_true",
                                                       "cover_usd_true", "genre_true", "occupancy", "is_synthetic"]),
        "syn_scout_truth": scout_truth,
    }
