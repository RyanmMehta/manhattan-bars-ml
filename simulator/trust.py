"""Time-ordered trust post-pass (specs §7.1-7.4): status flags, disputes, reputation, points, levels.

Outputs final syn_scout_reports, syn_disputes, syn_points_ledger, syn_scout_reputation_history,
syn_scouts and re-resolved bounty claims.
# SYNTHETIC: dispute rates/delays are placeholders (replace with the real dispute endpoint + moderator).
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from . import timeutil
from .nightloop import haversine_km


def level_for(points: float, levels: list) -> str:
    """Level name for all-time points (specs §7.2)."""
    name = levels[0][0]
    for n, th in levels:
        if points >= th:
            name = n
    return name


def flag_velocity(rep: pd.DataFrame, venues: pd.DataFrame, kmh: float) -> np.ndarray:
    """True where a scout's report implies > kmh from their previous report at another venue (specs §7.3.3)."""
    v = venues.set_index("venue_id")
    r = rep.sort_values(["scout_id", "ts"], kind="stable")
    prev_v = r.groupby("scout_id")["venue_id"].shift()
    prev_t = r.groupby("scout_id")["ts"].shift()
    has = prev_v.notna() & (prev_v != r["venue_id"])
    lat1 = v["lat"].reindex(prev_v).to_numpy()
    lon1 = v["lon"].reindex(prev_v).to_numpy()
    lat2 = v["lat"].reindex(r["venue_id"]).to_numpy()
    lon2 = v["lon"].reindex(r["venue_id"]).to_numpy()
    km = np.nan_to_num(haversine_km(lat1, lon1, lat2, lon2))
    hrs = ((r["ts"] - prev_t).dt.total_seconds() / 3600).to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        fast = has.to_numpy() & ((hrs <= 0) | (km / np.where(hrs > 0, hrs, np.nan) > kmh))
    out = pd.Series(np.nan_to_num(fast).astype(bool), index=r.index)
    return out.reindex(rep.index).to_numpy()


def _windows(rep: pd.DataFrame, ok: np.ndarray, win_min: float):
    """For each report: indices of *other scouts'* reports at the same venue within ±win (among `ok`)."""
    res = [np.array([], int)] * len(rep)
    t = rep["ts"].dt.as_unit("ns").astype("int64").to_numpy() / 6e10
    for _, idx in rep.groupby("venue_id").indices.items():
        idx = idx[np.argsort(t[idx], kind="stable")]
        tt = t[idx]
        sc = rep["scout_id"].to_numpy()[idx]
        lo = np.searchsorted(tt, tt - win_min, "left")
        hi = np.searchsorted(tt, tt + win_min, "right")
        for k, i in enumerate(idx):
            cand = idx[lo[k]:hi[k]]
            cand = cand[(sc[lo[k]:hi[k]] != sc[k]) & ok[cand]]
            res[i] = cand
    return res


def flag_outliers(rep: pd.DataFrame, ok: np.ndarray, sp: dict) -> np.ndarray:
    """|crowd - consensus| >= delta with >= min_others other reports in ±window (specs §7.3.4)."""
    wins = _windows(rep, ok, sp["consensus_window_min"])
    crowd = rep["crowd"].to_numpy(float)
    out = np.zeros(len(rep), bool)
    for i, o in enumerate(wins):
        if ok[i] and len(o) >= sp["outlier_min_others"]:
            out[i] = abs(crowd[i] - np.median(crowd[o])) >= sp["outlier_delta"]
    return out


def disputes(cfg: dict, rng, rep: pd.DataFrame, attrs: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    """Owner disputes on reports at claimed venues, biased to unflattering (low-crowd) reports."""
    dc, sp = cfg["disputes"], cfg["specs"]
    claimed = set(attrs.loc[attrs["is_claimed"] == 1, "venue_id"])
    rows = []
    for i, r in rep[rep["status"] == "accepted"].iterrows():
        if r["venue_id"] not in claimed:
            continue
        p = dc["rate"] * (dc["unflattering_mult"] if r["crowd"] <= 2 else 1.0)
        if rng.random() >= p:
            continue
        opened = r["ts"] + pd.Timedelta(hours=float(rng.uniform(*dc["open_delay_h"])))
        if opened > as_of:
            continue
        delay = float(rng.uniform(*dc["resolve_delay_h"]))
        if delay > sp["dispute_auto_reject_h"]:
            status, resolved = "auto_rejected", opened + pd.Timedelta(hours=sp["dispute_auto_reject_h"])
        else:
            status = "upheld" if rng.random() < dc["uphold_p"] else "rejected"
            resolved = opened + pd.Timedelta(hours=delay)
        if resolved > as_of:
            status, resolved = "open", pd.NaT
        rows.append({"report_id": r["report_id"], "opened_by": f"syn-o-{r['venue_id']}",
                     "reason": str(rng.choice(dc["reasons"])), "opened_at": opened.floor("min"),
                     "status": status, "resolved_at": resolved.floor("min") if pd.notna(resolved) else pd.NaT,
                     "is_synthetic": 1, "_i": i})
    df = pd.DataFrame(rows, columns=["report_id", "opened_by", "reason", "opened_at", "status", "resolved_at",
                                     "is_synthetic", "_i"])
    df = df.sort_values(["opened_at", "report_id"], kind="stable").reset_index(drop=True)
    df.insert(0, "dispute_id", [f"syn-d-{i + 1:05d}" for i in range(len(df))])
    return df


def _resolve_bounties(b: pd.DataFrame, rep: pd.DataFrame) -> pd.DataFrame:
    """Claims come from the loop (first verified report at the venue before expiry, v2 §E). The bounty pays
    only if that report is still not flagged/removed after the hold (specs §7.3.6): `_paid`."""
    b = b.sort_values(["created_at", "venue_id"], kind="stable").reset_index(drop=True)
    b.insert(0, "bounty_id", [f"syn-b-{i + 1:05d}" for i in range(len(b))])
    b["claimed_at"] = pd.to_datetime(b["claimed_at"], utc=True)
    key = rep.set_index(["venue_id", "scout_id", "ts"])
    rid, paid = [], []
    for _, x in b.iterrows():
        if pd.isna(x["claimed_by"]):
            rid.append(None); paid.append(False); continue
        r = key.loc[(x["venue_id"], x["claimed_by"], x["claimed_at"])]
        r = r.iloc[0] if isinstance(r, pd.DataFrame) else r
        rid.append(r["report_id"]); paid.append(r["status"] in ("accepted", "disputed"))
    b["_report_id"], b["_paid"] = rid, paid
    b["is_synthetic"] = 1
    return b


def _ledger(cfg, rep: pd.DataFrame, bounties: pd.DataFrame, disp: pd.DataFrame) -> pd.DataFrame:
    sp = cfg["specs"]
    hold = pd.Timedelta(minutes=sp["hold_minutes"])
    first = ~rep[rep["status"] != "flagged"].duplicated(["_night", "venue_id"])
    first = first.reindex(rep.index, fill_value=False)
    rows = []
    for i, r in rep.iterrows():
        aw = [(sp["points_accepted"], "accepted report")]
        if r["verified_presence"] == 1:
            aw.append((sp["points_verified"], "verified presence"))
        if first[i]:
            aw.append((sp["points_first"], "first report at venue tonight"))
        for p, why in aw:
            rows.append((r["scout_id"], r["report_id"], None, p, why, r["ts"]))
        if r["status"] == "flagged":
            rows.append((r["scout_id"], r["report_id"], None, -sum(p for p, _ in aw), "clawback: report flagged",
                         r["ts"] + hold))
            rows.append((r["scout_id"], r["report_id"], None, -sp["points_penalty"], "penalty: report flagged",
                         r["ts"] + hold))
        rep.at[i, "_awarded"] = sum(p for p, _ in aw)
    for _, b in bounties[bounties["_paid"]].iterrows():
        rows.append((b["claimed_by"], b["_report_id"], b["bounty_id"], int(b["points"]), "bounty claimed",
                     b["claimed_at"]))
    aw = rep.set_index("report_id")
    for _, d in disp[disp["status"] == "upheld"].iterrows():
        r = aw.loc[d["report_id"]]
        rows.append((r["scout_id"], d["report_id"], None, -int(r["_awarded"]), "clawback: dispute upheld",
                     d["resolved_at"]))
        rows.append((r["scout_id"], d["report_id"], None, -sp["points_penalty"], "penalty: dispute upheld",
                     d["resolved_at"]))
    df = pd.DataFrame(rows, columns=["scout_id", "report_id", "bounty_id", "points", "reason", "ts"])
    df = df.sort_values(["ts", "scout_id", "reason"], kind="stable").reset_index(drop=True)
    df.insert(0, "entry_id", [f"syn-p-{i + 1:06d}" for i in range(len(df))])
    df["is_synthetic"] = 1
    return df


def _rep_events(cfg, rep: pd.DataFrame, disp: pd.DataFrame) -> pd.DataFrame:
    sp = cfg["specs"]
    ok = rep["status"].isin(["accepted", "disputed"]).to_numpy()
    wins = _windows(rep, ok, sp["consensus_window_min"])
    crowd = rep["crowd"].to_numpy(float)
    ev = []
    for i, o in enumerate(wins):
        if ok[i] and len(o) >= sp["consensus_min_others"]:
            a = 1 - abs(crowd[i] - crowd[o].mean()) / 4
            delta = sp["rep_step"] * (a - sp["rep_target"]) + sp["rep_verified"] * rep["verified_presence"].iat[i]
            ev.append((rep["ts"].iat[i] + pd.Timedelta(minutes=sp["consensus_window_min"]),
                       rep["scout_id"].iat[i], delta))
    sid = rep.set_index("report_id")["scout_id"]
    for _, d in disp[disp["status"] == "upheld"].iterrows():
        ev.append((d["resolved_at"], sid[d["report_id"]], -sp["rep_dispute"]))
    return pd.DataFrame(ev, columns=["t", "scout_id", "delta"]).sort_values(["t", "scout_id"], kind="stable")


def run(cfg: dict, rng, raw: pd.DataFrame, bounties_raw: pd.DataFrame, pop: pd.DataFrame, attrs: pd.DataFrame,
        venues: pd.DataFrame, nights: list) -> dict:
    """Apply specs §7 in time order; return the final trust-related tables (UTC timestamps)."""
    sp = cfg["specs"]
    rep = raw.sort_values(["ts", "venue_id", "scout_id"], kind="stable").reset_index(drop=True)
    rep.insert(0, "report_id", [f"syn-r-{i + 1:06d}" for i in range(len(rep))])
    vel = flag_velocity(rep, venues, sp["velocity_kmh"])
    outl = flag_outliers(rep, ~vel, sp)
    rep["status"] = np.where(vel | outl, "flagged", "accepted")
    as_of = timeutil.night_bounds(nights[-1])[1]
    disp = disputes(cfg, rng, rep, attrs, as_of)
    st_map = {"upheld": "removed", "open": "disputed"}
    for _, d in disp.iterrows():
        if d["status"] in st_map:
            rep.at[d["_i"], "status"] = st_map[d["status"]]
    rep["is_synthetic"] = 1
    bounties = _resolve_bounties(bounties_raw, rep)
    rep["_awarded"] = 0
    ledger = _ledger(cfg, rep, bounties, disp)
    ev = _rep_events(cfg, rep, disp)
    hist, final = _history(cfg, rep, ledger, ev, nights)
    scouts, truth = _scouts(cfg, pop, rep, ledger, final, as_of)
    return {"syn_scout_reports": rep, "syn_bounties": bounties, "syn_disputes": disp, "syn_points_ledger": ledger,
            "syn_scout_reputation_history": hist, "syn_scouts": scouts, "syn_scout_truth": truth}


def _history(cfg, rep, ledger, ev, nights):
    sp = cfg["specs"]
    lo, hi = sp["rep_clip"]
    r: dict[str, float] = defaultdict(lambda: sp["rep_start"])
    ev_t, ev_s, ev_d = ev["t"].to_list(), ev["scout_id"].to_list(), ev["delta"].to_list()
    led = ledger.sort_values("ts", kind="stable")
    led_t = led["ts"].dt.as_unit("ns").astype("int64").to_numpy()
    led_cum = led.groupby("scout_id")["points"].cumsum().to_numpy()
    led_s = led["scout_id"].to_numpy()
    active = rep.groupby("_night")["scout_id"].unique()
    rows, k = [], 0
    for d in nights:
        end = timeutil.night_bounds(d)[1]
        while k < len(ev_t) and ev_t[k] <= end:
            r[ev_s[k]] = float(np.clip(r[ev_s[k]] + ev_d[k], lo, hi)); k += 1
        n = np.searchsorted(led_t, end.as_unit("ns").value, "right")
        last_pts = pd.Series(led_cum[:n], index=led_s[:n]).groupby(level=0).last() if n else pd.Series(dtype=float)
        for s in sorted(active.get(d, [])):
            pts = int(last_pts.get(s, 0))
            rows.append({"scout_id": s, "as_of_date": d.isoformat(), "reputation": round(r[s], 4), "points": pts,
                         "level": level_for(pts, sp["levels"]), "is_synthetic": 1})
    while k < len(ev_t):
        r[ev_s[k]] = float(np.clip(r[ev_s[k]] + ev_d[k], lo, hi)); k += 1
    return pd.DataFrame(rows, columns=["scout_id", "as_of_date", "reputation", "points", "level", "is_synthetic"]), r


def _scouts(cfg, pop, rep, ledger, final_rep, as_of):
    sp = cfg["specs"]
    p = pop[pop["joined_at"] <= as_of].sort_values("scout_id").reset_index(drop=True)
    pts = ledger.groupby("scout_id")["points"].sum()
    cnt = rep.groupby("scout_id").size()
    last = rep.groupby("scout_id")["ts"].max()
    s = pd.DataFrame({"scout_id": p["scout_id"], "display_name": p["display_name"], "joined_at": p["joined_at"]})
    s["reputation"] = [round(final_rep[x], 4) if x in final_rep else sp["rep_start"] for x in s["scout_id"]]
    s["points"] = s["scout_id"].map(pts).fillna(0).astype(int)
    s["level"] = [level_for(x, sp["levels"]) for x in s["points"]]
    s["reports_count"] = s["scout_id"].map(cnt).fillna(0).astype(int)
    s["last_active_at"] = s["scout_id"].map(last)
    s["is_synthetic"] = 1
    t = p[["scout_id", "archetype", "home_venue_id", "true_accuracy", "cohort_week", "churned_at"]].copy()
    t["churned_at"] = pd.to_datetime(t["churned_at"], utc=True)
    t["is_synthetic"] = 1
    return s, t
