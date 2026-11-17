"""What the app could know at `now=`: visible rows, derived `pending`/`disputed` status, open bounties,
live offers; plus a per-venue Live Venue State snapshot and `shift` (re-date the demo night).
Works on output-format tables (CSV/DB: local ISO strings) or internal ones (UTC Timestamps).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from . import timeutil
from .io import TS_COLS

APP_TABLES = ["syn_venue_attributes", "syn_scouts", "syn_users", "syn_scout_reports", "syn_venue_updates",
              "syn_feedback", "syn_bounties", "syn_venue_events", "syn_disputes", "syn_points_ledger",
              "syn_scout_reputation_history"]


def _utc(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, utc=True, format="ISO8601") if s.dtype == object or str(s.dtype).startswith(
        ("str", "string")) else pd.to_datetime(s, utc=True)


def parse(df: pd.DataFrame) -> pd.DataFrame:
    """Copy with every timestamp column as UTC Timestamps."""
    df = df.copy()
    for c in df.columns:
        if c in TS_COLS:
            df[c] = _utc(df[c])
    return df


def visible(tables: dict[str, pd.DataFrame], now) -> dict[str, pd.DataFrame]:
    """Rows visible at `now` (app tables only; syn_true_state / syn_scout_truth are never returned)."""
    now = timeutil.parse_ts(now)
    t = {k: parse(v) for k, v in tables.items() if k in APP_TABLES}
    out = {"syn_venue_attributes": t["syn_venue_attributes"], "syn_users": t.get("syn_users")}
    disp = t["syn_disputes"]
    disp = disp[disp["opened_at"] <= now].copy()
    resolved = disp["resolved_at"].notna() & (disp["resolved_at"] <= now)
    disp.loc[~resolved, "status"] = "open"
    disp.loc[~resolved, "resolved_at"] = pd.NaT
    out["syn_disputes"] = disp
    rep = t["syn_scout_reports"]
    rep = rep[rep["ts"] <= now + pd.Timedelta(minutes=2)].copy()
    stored = rep["status"]
    st = pd.Series("accepted", index=rep.index)
    st[stored == "flagged"] = "flagged"
    open_d = set(disp.loc[disp["status"] == "open", "report_id"])
    upheld = set(disp.loc[disp["status"] == "upheld", "report_id"])
    young = (now - rep["ts"]) < pd.Timedelta(minutes=30)
    st[(st == "accepted") & young] = "pending"
    st[rep["report_id"].isin(open_d) & (st != "flagged")] = "disputed"
    st[rep["report_id"].isin(upheld)] = "removed"
    rep["status"] = st
    out["syn_scout_reports"] = rep
    upd = t["syn_venue_updates"]
    upd = upd[upd["ts"] <= now].copy()
    expired = upd["offer_expires_at"].notna() & (upd["offer_expires_at"] <= now)
    upd.loc[expired, ["offer", "offer_expires_at"]] = None
    out["syn_venue_updates"] = upd
    b = t["syn_bounties"]
    b = b[b["created_at"] <= now].copy()
    claimed_later = b["claimed_at"].notna() & (b["claimed_at"] > now)
    b.loc[claimed_later, ["claimed_by", "claimed_at"]] = None
    out["syn_bounties"] = b
    out["open_bounties"] = b[(b["expires_at"] > now) & b["claimed_at"].isna()]
    for k, c in (("syn_venue_events", "ts"), ("syn_points_ledger", "ts"), ("syn_feedback", "recommended_at")):
        if k in t:
            out[k] = t[k][t[k][c] <= now]
    night = timeutil.night_of(now)
    h = t["syn_scout_reputation_history"]
    out["syn_scout_reputation_history"] = h[h["as_of_date"].astype(str) < night.isoformat()]
    s = t["syn_scouts"]
    out["syn_scouts"] = s[s["joined_at"] <= now]
    return out


def reputation_as_of(seen: dict) -> pd.Series:
    """Latest completed-night reputation per scout (default 0.5 handled by caller)."""
    h = seen["syn_scout_reputation_history"].sort_values("as_of_date")
    return h.groupby("scout_id")["reputation"].last()


def live_states(seen: dict, now) -> tuple[list[dict], str]:
    """Live Venue State per launch venue at `now` via recs.live_state if importable, else the fallback."""
    now = timeutil.parse_ts(now)
    rep = seen["syn_scout_reports"].copy()
    rep["reputation"] = rep["scout_id"].map(reputation_as_of(seen)).fillna(0.5)
    upd = seen["syn_venue_updates"]
    try:  # prefer the real implementation (ml-recs) when it is importable
        from recs import live_state as recs_ls  # type: ignore
        states = recs_ls.compute_all(rep, upd, now)
        return list(states), "recs"
    except Exception:  # noqa: BLE001 - SYNTHETIC: fallback mirror of specs §5 until recs is importable
        from . import _live_state
        by_v = dict(tuple(rep.groupby("venue_id")))
        out = [_live_state.compute(v, by_v.get(v), None, now) for v in seen["syn_venue_attributes"]["venue_id"]]
        return out, "fallback"


def shift(tables: dict[str, pd.DataFrame], to_date: date, src_night: date = date(2026, 11, 14)) -> dict:
    """Re-date rows of the demo night onto `to_date`, keeping local time of night (still synthetic)."""
    s0, s1 = timeutil.night_bounds(src_night)
    days = (to_date - src_night).days
    out = {}
    for k in ("syn_scout_reports", "syn_venue_updates", "syn_bounties", "syn_venue_events", "syn_disputes",
              "syn_points_ledger", "syn_feedback"):
        if k not in tables:
            continue
        df = parse(tables[k])
        key = {"syn_bounties": "created_at", "syn_disputes": "opened_at", "syn_feedback": "recommended_at"}.get(k, "ts")
        lo = s0 - pd.Timedelta(hours=4) if k == "syn_venue_updates" else s0
        df = df[(df[key] >= lo) & (df[key] < s1)].copy()
        for c in df.columns:
            if c in TS_COLS:
                loc = df[c].dt.tz_convert(timeutil.TZ).dt.tz_localize(None) + pd.Timedelta(days=days)
                df[c] = loc.dt.tz_localize(timeutil.TZ, ambiguous="NaT", nonexistent="shift_forward").dt.tz_convert("UTC")
        out[k] = df
    return out
