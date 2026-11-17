"""Model chaining: clusters -> crowd-model features -> predicted_crowd -> live state -> scoring -> routing.

snapshots(reports, updates, start, end, step_minutes=30) -> DataFrame (CONTRACTS v2.2 §J columns) so live-sim's
    data/synthetic_live/demo_night_snapshots.csv uses exactly recs.live_state.
run(now, prefs, source) -> {"states", "recommendations", "plan"} end to end (CLI demo).
ablation(tables) -> dict for reports/chaining.md.
"""
from __future__ import annotations

from datetime import timedelta

import pandas as pd

from . import config as C
from . import live_state, routing, scoring
from .inputs import rows
from .timeutil import iso, to_dt

SNAPSHOT_COLS = ["venue_id", "snapshot_ts", "crowd", "dancing", "line_minutes", "vibe_score", "confidence", "n_reports",
                 "is_synthetic"]


def _window(df: pd.DataFrame | None, now, before=C.CUTOFF_MINUTES, after=C.FUTURE_SKEW_MINUTES):
    """Cheap pre-filter of rows to the eligible window (live_state re-checks exactly)."""
    if df is None or len(df) == 0:
        return df
    ts = pd.to_datetime(df["ts"], utc=True)
    now = pd.Timestamp(to_dt(now))
    return df[(ts >= now - pd.Timedelta(minutes=before + 1)) & (ts <= now + pd.Timedelta(minutes=after + 1))]


def snapshots(reports, updates, start, end, step_minutes: int = 30, venue_ids=None) -> pd.DataFrame:
    """Live state every `step_minutes` from start to end inclusive (default Sat Nov 14 20:00-03:00 -> 15 rows/venue)."""
    # SYNTHETIC: called on live-sim syn_scout_reports / syn_venue_updates; real data computes live instead.
    rep = reports if isinstance(reports, pd.DataFrame) else pd.DataFrame(rows(reports))
    upd = updates if isinstance(updates, pd.DataFrame) else pd.DataFrame(rows(updates))
    t, end = to_dt(start), to_dt(end)
    syn_in = any(bool(x) for df in (rep, upd) if "is_synthetic" in df for x in df["is_synthetic"].fillna(0))
    ids = sorted(set(venue_ids or []) | set(rep.get("venue_id", [])) | set(upd.get("venue_id", [])), key=str)
    out = []
    while t <= end:
        sts = live_state.compute_all(_window(rep, t), _window(upd, t), t, venue_ids=ids)
        for s in sts:
            out.append({"venue_id": s["venue_id"], "snapshot_ts": iso(t), "crowd": s["crowd"], "dancing": s["dancing"],
                        "line_minutes": s["line_minutes"], "vibe_score": s["vibe_score"], "confidence": s["confidence"],
                        "n_reports": s["n_reports"], "is_synthetic": int(bool(s["is_synthetic"]) or syn_in)})
        t = t + timedelta(minutes=step_minutes)
    return pd.DataFrame(out, columns=SNAPSHOT_COLS)


def run(now=C.DEMO_NOW, prefs: dict | None = None, source: str = "auto", n_stops: int = 3, use_model: bool = True) -> dict:
    """End-to-end pipeline at `now` on live-sim (or stub) data."""
    from . import data
    now = to_dt(now)
    t = data.live_tables(source)
    reports = data.reports_with_reputation(source)  # live path: current reputation, as the backend does
    venues = data.venues_for_scoring(source)
    pred = "auto" if use_model else None
    states = live_state.compute_all(_window(reports, now), _window(t["syn_venue_updates"], now), now,
                                    venue_ids=[v["venue_id"] for v in venues], predictor=pred)
    prefs = dict(prefs or {})
    recs = scoring.recommend(prefs, states, venues, now)
    plan = routing.plan_night(prefs, states, venues, prefs.get("start_time") or now, n_stops=n_stops, predictor=pred)
    return {"now": iso(now), "source": t["_source"], "states": states, "recommendations": recs, "plan": plan}


def ablation(tables: dict, prefs: dict) -> dict:
    """(1) crowd model with/without cluster feature; (2) routing with/without predicted crowd, scored on truth."""
    from . import crowd_model, data
    out: dict = {}
    df = crowd_model.build_table(tables)
    hold = [n for n in C.HOLDOUT_NIGHTS if n in set(df["night"])]
    tr, te = df[~df["night"].isin(hold)], df[df["night"].isin(hold)]
    with_c = crowd_model.GBModel().fit(tr).predict(te)
    no_c = crowd_model.GBModel().fit(tr.assign(cluster_id=None)).predict(te.assign(cluster_id=None))
    base = crowd_model.Baseline().fit(tr).predict(te)
    mae = lambda p: float(abs(te["crowd"].to_numpy() - p).mean())  # noqa: E731
    out["crowd_model"] = {"with_clusters": mae(with_c), "without_clusters": mae(no_c), "baseline": mae(base)}

    truth = crowd_model.true_crowd_lookup(tables)  # evaluation only
    if truth is None or not crowd_model.available():
        out["routing"] = None
        return out
    reports = data.reports_with_reputation()
    venues = data.venues_for_scoring()
    vids = [v["venue_id"] for v in venues]
    rows_ = []
    for night in hold:
        for hhmm in ("21:00", "22:00", "23:00", "23:30"):
            now = to_dt(f"{night}T{hhmm}:00")
            sts = live_state.compute_all(_window(reports, now), _window(tables["syn_venue_updates"], now), now, venue_ids=vids)
            for label, pred in (("current state only", None), ("with crowd model", crowd_model.predict)):
                plan = routing.plan_night(prefs, sts, venues, now, predictor=pred)
                # realised value: re-score each stop with the TRUE crowd at arrival (eval only)
                ctx = routing.build_ctx(prefs, sts, venues, now)
                val = 0.0
                fit = []
                for s in plan:
                    tc = truth(s["venue_id"], s["arrive_at"])
                    st = dict(ctx.state(s["venue_id"]), crowd=tc, confidence=1.0)
                    r = scoring.score_one(prefs, st, ctx.venues[s["venue_id"]], s["arrive_at"])
                    val += r["_rs"] - C.WALK_COST_PER_KM * s["distance_km"]
                    if tc is not None:
                        fit.append(1 - abs(tc - prefs.get("crowd_pref", 3)) / 4)
                rows_.append({"night": night, "start": hhmm, "variant": label, "stops": len(plan),
                              "realised_objective": round(val, 1), "true_crowd_fit": round(sum(fit) / max(1, len(fit)), 3)})
    r = pd.DataFrame(rows_)
    out["routing"] = {"rows": rows_, "mean": r.groupby("variant")[["realised_objective", "true_crowd_fit"]].mean().round(3)
                      .reset_index().to_dict(orient="records")}
    return out
