"""Schema, integrity, specs-rule and realism checks -> validation.json (non-zero CLI exit on failure)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import replay, schema, timeutil
from .config import DEMO_NOW, GENRES


def _chk(out: list, name: str, ok, value=None, target=None, skip: bool = False) -> None:
    out.append({"check": name, "ok": None if skip else bool(ok), "value": value, "target": target,
                **({"skipped": True} if skip else {})})


def run(tables: dict[str, pd.DataFrame], cfg: dict, meta: dict | None = None) -> dict:
    """`tables` in output format (as written to CSV) or internal; returns the validation report."""
    meta = meta or {}
    t = {k: _floats(replay.parse(v)) for k, v in tables.items() if k in schema.TABLES}
    res: list[dict] = []
    for name in schema.TABLES:
        errs = schema.check(tables[name][schema.TABLES[name]] if name in tables else pd.DataFrame(), name) \
            if name in tables else [f"{name}: missing"]
        _chk(res, f"schema:{name}", not errs, "; ".join(errs)[:300] or "ok")
    _integrity(res, t)
    _specs_rules(res, t, cfg)
    _realism(res, t, cfg, tables)
    _demo(res, tables, cfg)
    full = (cfg.get("nights") in (None, 36))
    _people(res, t, cfg, full)
    if meta.get("csv_bytes") is not None:
        _chk(res, "csv_total_mb<=30", meta["csv_bytes"] / 1e6 <= 30, round(meta["csv_bytes"] / 1e6, 2), 30)
    if meta.get("build_seconds") is not None:
        _chk(res, "build_seconds<60", meta["build_seconds"] < 60, meta["build_seconds"], 60, skip=not full)
    failed = [r["check"] for r in res if r["ok"] is False]
    return {"ok": not failed, "failed": failed, "n_checks": len(res), "checks": res}


def _floats(df: pd.DataFrame) -> pd.DataFrame:
    for c in df.columns:
        if str(df[c].dtype) in ("Int64", "Int32", "Float64"):
            df[c] = df[c].astype(float)
    return df


def _integrity(res, t):
    vids = set(t["syn_venue_attributes"]["venue_id"])
    sids = set(t["syn_scouts"]["scout_id"])
    uids = set(t["syn_users"]["user_id"])
    rids = set(t["syn_scout_reports"]["report_id"])
    for k in ("syn_scout_reports", "syn_venue_updates", "syn_feedback", "syn_bounties", "syn_venue_events",
              "syn_true_state"):
        _chk(res, f"fk:{k}.venue_id", t[k]["venue_id"].isin(vids).all())
    _chk(res, "fk:reports.scout_id", t["syn_scout_reports"]["scout_id"].isin(sids).all())
    _chk(res, "fk:ledger.scout_id", t["syn_points_ledger"]["scout_id"].isin(sids).all())
    _chk(res, "fk:disputes.report_id", t["syn_disputes"]["report_id"].isin(rids).all())
    _chk(res, "fk:feedback.user_id", t["syn_feedback"]["user_id"].isin(uids).all())
    ev = t["syn_venue_events"]["user_id"].dropna()
    _chk(res, "fk:events.user_id", ev.isin(uids).all())
    g = set()
    for c in (t["syn_venue_attributes"]["genres"], t["syn_venue_updates"]["genres"]):
        g |= {x for s in c.dropna() for x in str(s).split("|")}
    g |= set(t["syn_scout_reports"]["music_genre"].dropna())
    _chk(res, "genres_in_vocabulary", g <= set(GENRES), sorted(g - set(GENRES)))
    _chk(res, "genres_json_17", len(GENRES) == 17 and len(set(GENRES)) == 17, len(GENRES), 17)
    allsyn = all((v["is_synthetic"] == 1).all() for v in t.values())
    _chk(res, "all_rows_is_synthetic", allsyn)


def _specs_rules(res, t, cfg):
    sp = cfg["specs"]
    r = t["syn_scout_reports"]
    d = r["distance_m"]
    ver = (d.notna() & (d <= sp["presence_radius_m"])).astype(int)
    _chk(res, "verified_iff_distance<=150", (ver == r["verified_presence"]).all())
    led = t["syn_points_ledger"].groupby("scout_id")["points"].sum()
    s = t["syn_scouts"].set_index("scout_id")["points"]
    _chk(res, "ledger_sums_to_points", (s - led.reindex(s.index).fillna(0) == 0).all())
    b = t["syn_bounties"]
    life = (b["expires_at"] - b["created_at"]).dt.total_seconds() / 60
    _chk(res, "bounty_expiry_60min", (life == sp["bounty_expire_min"]).all())
    if len(b):
        times = b["created_at"].unique()
        end = b["claimed_at"].fillna(b["expires_at"]).where(b["claimed_at"].fillna(b["expires_at"]) < b["expires_at"],
                                                             b["expires_at"])
        mx = max(int(((b["created_at"] <= x) & (end > x)).sum()) for x in times)
        _chk(res, "bounties_max_open<=8", mx <= sp["bounty_max_open"], mx, sp["bounty_max_open"])
    rr = r.sort_values(["scout_id", "venue_id", "ts"])
    gap = rr.groupby(["scout_id", "venue_id"])["ts"].diff().dt.total_seconds() / 60
    _chk(res, "rate_limit_per_venue_20min", (gap.dropna() >= sp["rate_per_venue_minutes"]).all())
    st = r["status"].value_counts().to_dict()
    _chk(res, "status_values", set(st) <= schema.REPORT_STATUS_STORED, st)


def _slot_join(t):
    r = t["syn_scout_reports"].copy()
    r["slot"] = r["ts"].dt.floor("15min")
    tr = t["syn_true_state"][["venue_id", "ts", "crowd_true"]].rename(columns={"ts": "slot"})
    return r.merge(tr, on=["venue_id", "slot"], how="left")


def _realism(res, t, cfg, tables):
    r = t["syn_scout_reports"]
    h = pd.Series(timeutil.local_hour(r["ts"]), index=r.index)
    night = r["ts"].map(timeutil.night_of)
    peak = h.floordiv(1).groupby(night).agg(lambda x: x.value_counts().idxmax())
    share = float(((peak >= 22) & (peak < 25)).mean())
    _chk(res, "report_peak_22_to_01", share >= 0.9, round(share, 3), ">=0.9 of nights")
    tr = t["syn_true_state"]
    th = pd.Series(timeutil.local_hour(tr["ts"]), index=tr.index)
    wd = tr["ts"].map(lambda x: timeutil.night_of(x).weekday())
    at23 = tr[th == 23.0].groupby(wd[th == 23.0])["crowd_true"].mean()
    if len(at23) == 3:
        _chk(res, "crowd_23h_sat>=fri>=thu", at23[5] >= at23[4] >= at23[3], at23.round(2).to_dict())
    sty = tr["venue_id"].map(t["syn_venue_attributes"].set_index("venue_id")["style"])
    late, early = {"club", "dive"}, {"cocktail", "restaurant-bar"}
    for hh, name, hi_set, lo_set in ((25.0, "01:00 club/dive > cocktail/rest", late, early),
                                     (20.5, "20:30 cocktail/rest > club/dive", early, late)):
        m = th == hh
        a = tr.loc[m & sty.isin(hi_set), "crowd_true"].astype(float).mean()
        b = tr.loc[m & sty.isin(lo_set), "crowd_true"].astype(float).mean()
        if np.isnan(a) or np.isnan(b):
            _chk(res, name, False, None, skip=True)
        else:
            _chk(res, name, a > b, [round(float(a), 2), round(float(b), 2)])
    j = _slot_join(t)
    arch = j["scout_id"].map(t["syn_scout_truth"].set_index("scout_id")["archetype"])
    mae = (j["crowd"] - j["crowd_true"]).abs().groupby(arch).mean().round(3).to_dict()
    _chk(res, "honest_mae<=0.6", mae.get("honest", 9) <= 0.6, mae.get("honest"), 0.6)
    bad = [mae[k] for k in ("gamer", "shill") if k in mae]
    _chk(res, "gamer_shill_mae>=1.2", bool(bad) and min(bad) >= 1.2, mae, 1.2)
    o = tr[(th >= 21) & (th < 26) & tr["_open"]] if "_open" in tr else tr[(th >= 21) & (th < 26)]
    cells = o.assign(s=o["ts"].dt.floor("30min"))[["venue_id", "s"]].drop_duplicates()
    rep = r.assign(s=r["ts"].dt.floor("30min"))[["venue_id", "s"]].drop_duplicates().assign(x=1)
    empty = float(cells.merge(rep, how="left", on=["venue_id", "s"])["x"].isna().mean())
    _chk(res, "empty_venue_slots>=20%", empty >= 0.2, round(empty, 3), 0.2)
    for c, target in (("cover_usd", 0.6), ("music_genre", 0.4)):
        nr = float(r[c].isna().mean())
        _chk(res, f"null_rate:{c}~{target}", abs(nr - target) <= 0.15, round(nr, 3), target)
    fb = tables["syn_feedback"]
    if "_fit" in fb:
        x = fb.dropna(subset=["rating"])
        rho = float(pd.Series(x["_fit"].to_numpy()).rank().corr(pd.Series(x["rating"].astype(float).to_numpy()).rank()))
        _chk(res, "feedback_spearman>=0.3", rho >= 0.3, round(rho, 3), 0.3)


def _demo(res, tables, cfg):
    ok_range = timeutil.nights(cfg.get("nights"))[-1].isoformat() == "2026-11-14"
    seen = replay.visible({k: v for k, v in tables.items() if k in replay.APP_TABLES}, DEMO_NOW)
    now = timeutil.parse_ts(DEMO_NOW)
    r = seen["syn_scout_reports"]
    fresh = r[r["ts"] >= now - pd.Timedelta(minutes=60)]["venue_id"].nunique()
    _chk(res, "demo_now_fresh_venues>=25", fresh >= 25, int(fresh), 25, skip=not ok_range)
    nb = len(seen["open_bounties"])
    _chk(res, "demo_now_open_bounties>=3", nb >= 3, nb, 3, skip=not ok_range)
    _chk(res, "demo_now_pending_reports", (r["status"] == "pending").any(), int((r["status"] == "pending").sum()))


def _people(res, t, cfg, full):
    st = t["syn_scout_truth"]
    r = t["syn_scout_reports"]
    last = r.groupby("scout_id")["ts"].max()
    ch = st.dropna(subset=["churned_at"]).set_index("scout_id")["churned_at"]
    after = (last.reindex(ch.index) > ch).sum()
    _chk(res, "no_reports_after_churned_at", after == 0, int(after))
    share = float(st["churned_at"].notna().mean())
    _chk(res, "churn_share_40_60%", 0.4 <= share <= 0.6, round(share, 3), [0.4, 0.6], skip=not full)
    end = timeutil.night_bounds(timeutil.LAST_NIGHT)[1]
    sc = t["syn_scouts"].set_index("scout_id")
    label = (sc["last_active_at"].isna() & (sc["joined_at"] < end - pd.Timedelta(days=21))) | \
            (sc["last_active_at"] < end - pd.Timedelta(days=21))
    latent = st.set_index("scout_id")["churned_at"].reindex(sc.index).notna()
    elig = sc["joined_at"] < end - pd.Timedelta(days=21)
    agree = float((label[elig] == latent[elig]).mean()) if elig.any() else 1.0
    _chk(res, "churn_label21_vs_latent>=80%", agree >= 0.8, round(agree, 3), 0.8, skip=not full)
    first = r.groupby("scout_id")["ts"].min()
    coh = st.set_index("scout_id")["cohort_week"]
    j = sc["joined_at"]
    wk4 = j + pd.Timedelta(days=21)
    alive = pd.Series({s: bool(((r["scout_id"] == s) & (r["ts"] >= wk4[s]) &
                               (r["ts"] < wk4[s] + pd.Timedelta(days=7))).any()) for s in sc.index if
                       wk4[s] + pd.Timedelta(days=7) <= end and s in first.index})
    ret = float(alive.mean()) if len(alive) else 0.0
    _chk(res, "week4_retention_35_60%", 0.35 <= ret <= 0.6, round(ret, 3), [0.35, 0.6], skip=not full)


def write(report: dict, out_dir: Path) -> Path:
    p = Path(out_dir) / "validation.json"
    p.write_text(json.dumps(report, indent=2, default=str) + "\n")
    return p
