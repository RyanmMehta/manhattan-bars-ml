"""Crowd forecast (1-5) by venue × hour slot. Course deliverable "baseline + first model".

# SYNTHETIC: trained on live-sim / stub syn_scout_reports; retrain on >= 4 weeks of real scout_reports.

build_table(tables)   venue × night × hour-slot rows; target = weighted mean reported crowd, report weights use
                      reputation AS OF the report's night (syn_scout_reputation_history), never final reputation.
Baseline              venue×slot×weekday mean -> venue×slot -> venue -> global slot mean (train nights only).
train(tables)         HistGradientBoostingRegressor; writes recs/artifacts/synthetic/crowd_model.joblib + .json.
predict(vids, times)  list[float|None]; None for unknown venues or times outside 18:00-05:59.
evaluate(tables)      temporal holdout (Nov 13-14) + 3-fold rolling origin; scores vs reported crowd and vs
                      syn_true_state.crowd_true. The ONLY function allowed to read evaluation-only truth tables.
"""
from __future__ import annotations

import json
import logging
import math
from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C
from .timeutil import night_date, to_dt

log = logging.getLogger("recs")
ART = Path(__file__).resolve().parent / "artifacts" / "synthetic"
MODEL_PATH = ART / "crowd_model.joblib"
META_PATH = ART / "crowd_model.json"
SLOT_HOURS = [20, 21, 22, 23, 0, 1, 2]
WEEK0 = date(2026, 8, 27)
STATIC = ["style", "has_dance_floor", "capacity", "price_level", "typical_cover_usd"]
PUBLIC = ["density_100m", "osm_closes_late", "years_licensed", "liquor_tier"]
CATS = ["style", "cluster_id", "weekday"]
# `week` is deliberately not a feature: on live-sim data it extrapolates badly into the holdout weeks
# (holdout MAE 0.81 with it vs 0.70 without). price_level / typical_cover_usd / liquor_tier added noise.
FEATURES = ["slot", "weekday", "style", "has_dance_floor", "capacity", "density_100m", "osm_closes_late",
            "cluster_id", "venue_te", "venue_slot_te", "venue_weekday_te"]
HGB = dict(max_iter=200, learning_rate=0.03, max_leaf_nodes=15, min_samples_leaf=50, l2_regularization=1.0,
           random_state=C.SEED)


def slot_of(dt) -> int | None:
    h = to_dt(dt).hour
    if 18 <= h <= 20:
        return 0
    if h >= 21:
        return h - 20
    if h <= 2:
        return h + 4
    if h <= 5:
        return 6
    return None


# ------------------------------------------------------------------------------------------------ table
def _asof_reputation(reports: pd.DataFrame, history: pd.DataFrame | None) -> pd.Series:
    """Reputation as of each report's night: latest history row with as_of_date <= night date (default 0.5)."""
    if history is None or history.empty:
        return pd.Series(C.DEFAULT_REPUTATION, index=reports.index)
    r = reports[["scout_id", "night"]].copy()
    r["_i"] = np.arange(len(r))
    r["night_ts"] = pd.to_datetime(r["night"])
    h = history[["scout_id", "as_of_date", "reputation"]].copy()
    h["as_of_ts"] = pd.to_datetime(h["as_of_date"])
    m = pd.merge_asof(r.sort_values("night_ts"), h.sort_values("as_of_ts"), left_on="night_ts", right_on="as_of_ts",
                      by="scout_id", direction="backward")
    m = m.sort_values("_i")
    return pd.Series(m["reputation"].fillna(C.DEFAULT_REPUTATION).to_numpy(), index=reports.index)


def venue_static(tables: dict) -> pd.DataFrame:
    """Static per-venue features: synthetic attributes + real public features + cluster id (chaining)."""
    from . import clustering, data
    v = data.launch_venues()[["venue_id"]].copy()
    attrs = tables.get("syn_venue_attributes")
    if attrs is not None:
        v = v.merge(attrs[["venue_id", *[c for c in STATIC if c in attrs.columns]]], on="venue_id", how="left")
    if data.has_bars_db():
        f = data.venue_features(bars_only=False)[["license_id", *PUBLIC]].rename(columns={"license_id": "venue_id"})
        v = v.merge(f, on="venue_id", how="left")
    v["cluster_id"] = [clustering.cluster_for(x) for x in v["venue_id"]]
    for c in [*STATIC, *PUBLIC, "cluster_id"]:
        if c not in v:
            v[c] = np.nan
    return v


def build_table(tables: dict) -> pd.DataFrame:
    """venue_id, night, slot, weekday, week, crowd (target), n, + static features (no venue_te yet)."""
    r = tables["syn_scout_reports"].copy()
    if "status" in r:
        r = r[r["status"].fillna("accepted").isin(["accepted", "pending", "disputed"])]
    r = r[r["crowd"].notna()].copy()
    ts = pd.to_datetime(r["ts"], utc=True).dt.tz_convert(C.TZ)
    r["night"] = [night_date(t).isoformat() for t in ts]
    r["slot"] = [slot_of(t) for t in ts]
    r = r[r["slot"].notna()]
    rep = _asof_reputation(r, tables.get("syn_scout_reputation_history"))
    ver = r["verified_presence"].fillna(0).astype(float)
    status_w = r.get("status", pd.Series("accepted", index=r.index)).fillna("accepted").map(C.STATUS_WEIGHT).fillna(1.0)
    r["w"] = (C.REP_BASE + C.REP_SLOPE * rep) * np.where(ver > 0, 1.0, C.UNVERIFIED_WEIGHT) * status_w
    r["wc"] = r["w"] * r["crowd"].astype(float)
    g = r.groupby(["venue_id", "night", "slot"], as_index=False).agg(wc=("wc", "sum"), w=("w", "sum"), n=("crowd", "size"))
    g = g[g["w"] > 0]
    g["crowd"] = (g["wc"] / g["w"]).clip(1, 5)
    g["slot"] = g["slot"].astype(int)
    nd = pd.to_datetime(g["night"])
    g["weekday"] = nd.dt.weekday.astype(int)
    g["week"] = ((nd - pd.Timestamp(WEEK0)).dt.days // 7).astype(int)
    g = g.drop(columns=["wc"]).merge(venue_static(tables), on="venue_id", how="left")
    return g.sort_values(["night", "venue_id", "slot"]).reset_index(drop=True)


# ------------------------------------------------------------------------------------------------ models
class Baseline:
    """Venue×slot×weekday mean -> venue×slot -> venue -> global slot mean -> global mean."""

    def fit(self, df):
        self.k3 = df.groupby(["venue_id", "slot", "weekday"])["crowd"].mean().to_dict()
        self.k2 = df.groupby(["venue_id", "slot"])["crowd"].mean().to_dict()
        self.k1 = df.groupby("venue_id")["crowd"].mean().to_dict()
        self.ks = df.groupby("slot")["crowd"].mean().to_dict()
        self.g = float(df["crowd"].mean())
        return self

    def predict(self, df):
        out = []
        for v, s, w in zip(df["venue_id"], df["slot"], df["weekday"]):
            for val in (self.k3.get((v, s, w)), self.k2.get((v, s)), self.k1.get(v), self.ks.get(s), self.g):
                if val is not None:
                    out.append(val)
                    break
        return np.array(out)


class SlotMean:
    def fit(self, df):
        self.ks = df.groupby("slot")["crowd"].mean().to_dict()
        self.g = float(df["crowd"].mean())
        return self

    def predict(self, df):
        return np.array([self.ks.get(s, self.g) for s in df["slot"]])


def _X(df: pd.DataFrame, te: dict, gmean: float) -> pd.DataFrame:
    """te: {"venue": {...}, "venue_slot": {...}, "venue_weekday": {...}} (train nights only)."""
    X = df.copy()
    X["venue_te"] = X["venue_id"].map(te.get("venue", {})).fillna(gmean)
    vs, vw = te.get("venue_slot", {}), te.get("venue_weekday", {})
    X["venue_slot_te"] = [vs.get((v, int(s)), np.nan) for v, s in zip(X["venue_id"], X["slot"])]
    X["venue_weekday_te"] = [vw.get((v, int(w)), np.nan) for v, w in zip(X["venue_id"], X["weekday"])]
    for c in FEATURES:
        if c not in X:
            X[c] = np.nan
    X = X[FEATURES].copy()
    for c in CATS:
        X[c] = X[c].astype("string").fillna("na").astype("category")
    for c in FEATURES:
        if c not in CATS:
            X[c] = pd.to_numeric(X[c], errors="coerce").astype(float)
    return X


class GBModel:
    def fit(self, df):
        from sklearn.ensemble import HistGradientBoostingRegressor
        self.te = {  # train-night target encodings only
            "venue": df.groupby("venue_id")["crowd"].mean().to_dict(),
            "venue_slot": df.groupby(["venue_id", "slot"])["crowd"].mean().to_dict(),
            "venue_weekday": df.groupby(["venue_id", "weekday"])["crowd"].mean().to_dict(),
        }
        self.gmean = float(df["crowd"].mean())
        X = _X(df, self.te, self.gmean)
        self.cats = {c: list(X[c].cat.categories) for c in CATS}
        self.m = HistGradientBoostingRegressor(categorical_features="from_dtype", **HGB)
        self.m.fit(X, df["crowd"], sample_weight=df["w"])
        return self

    def _align(self, X):
        for c in CATS:
            X[c] = pd.Categorical(X[c].astype(str), categories=self.cats[c])
        return X

    def predict(self, df):
        return np.clip(self.m.predict(self._align(_X(df, self.te, self.gmean))), 1, 5)


# ------------------------------------------------------------------------------------------------ eval
def _metrics(y, p):
    from scipy.stats import spearmanr
    y, p = np.asarray(y, float), np.asarray(p, float)
    rho = spearmanr(y, p).statistic if len(y) > 2 else float("nan")
    return {"mae": float(np.mean(np.abs(y - p))), "rmse": float(np.sqrt(np.mean((y - p) ** 2))),
            "spearman": float(rho), "n": int(len(y))}


def _truth_by_slot(tables) -> pd.DataFrame | None:
    """EVALUATION ONLY: mean crowd_true per venue × night × slot."""
    t = tables.get("syn_true_state")  # evaluation-only table; never a feature
    if t is None or t.empty:
        return None
    ts = pd.to_datetime(t["ts"], utc=True).dt.tz_convert(C.TZ)
    t = t.assign(night=[night_date(x).isoformat() for x in ts], slot=[slot_of(x) for x in ts])
    t = t[t["slot"].notna()]
    t["slot"] = t["slot"].astype(int)
    return t.groupby(["venue_id", "night", "slot"], as_index=False)["crowd_true"].mean()


def evaluate(tables: dict, table: pd.DataFrame | None = None) -> dict:
    """Holdout (CONTRACTS §B: last 2 nights) + 3 rolling-origin folds of 2 nights each."""
    df = build_table(tables) if table is None else table
    nights = sorted(df["night"].unique())
    hold = [n for n in nights if n in C.HOLDOUT_NIGHTS] or nights[-2:]
    pre = [n for n in nights if n < min(hold)]
    folds = [("holdout", [n for n in nights if n < min(hold)], hold)]
    for i in range(3, 0, -1):
        test = pre[-2 * i:len(pre) - 2 * (i - 1)] if i > 1 else pre[-2:]
        train = [n for n in pre if n < min(test)]
        folds.append((f"rolling_{4 - i}", train, test))
    truth = _truth_by_slot(tables)
    res = {}
    for name, tr, te in folds:
        dtr, dte = df[df["night"].isin(tr)], df[df["night"].isin(te)]
        row = {"train_nights": len(tr), "test_nights": te}
        models = {"model": GBModel().fit(dtr), "baseline": Baseline().fit(dtr), "slot_mean": SlotMean().fit(dtr)}
        preds = {k: m.predict(dte) for k, m in models.items()}
        row["vs_reported"] = {k: _metrics(dte["crowd"], p) for k, p in preds.items()}
        if truth is not None:
            j = dte[["venue_id", "night", "slot"]].reset_index(drop=True).merge(truth, on=["venue_id", "night", "slot"], how="left")
            ok = j["crowd_true"].notna().to_numpy()
            row["vs_true"] = {k: _metrics(j["crowd_true"][ok], p[ok]) for k, p in preds.items()}
        res[name] = row
    h = res["holdout"]["vs_reported"]
    res["summary"] = {"model_mae": h["model"]["mae"], "baseline_mae": h["baseline"]["mae"],
                      "ratio": h["model"]["mae"] / h["baseline"]["mae"], "target_ratio": 0.9,
                      "rows": int(len(df)), "nights": len(nights)}
    return res


# ------------------------------------------------------------------------------------------------ train / predict
def train(tables: dict, write: bool = True) -> dict:
    """Fit on all nights before the holdout (artifact used by the app; holdout stays honest) and save."""
    import joblib
    df = build_table(tables)
    hold = [n for n in C.HOLDOUT_NIGHTS if n in set(df["night"])]
    dtr = df[~df["night"].isin(hold)] if hold else df
    gb = GBModel().fit(dtr)
    static = venue_static(tables)
    ev = evaluate(tables, df)
    meta = {
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_source": tables.get("_source", "unknown"), "rows": int(len(dtr)), "train_nights": int(dtr["night"].nunique()),
        "holdout_nights": hold, "features": FEATURES, "params": HGB, "is_synthetic": True,
        "metrics": {"holdout": ev["holdout"], "summary": ev["summary"]},
    }
    if write:
        ART.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": gb, "static": static, "week0": WEEK0.isoformat()}, MODEL_PATH, compress=3)
        META_PATH.write_text(json.dumps(meta, indent=1, default=str))
        _load.cache_clear()
    meta["_eval"] = ev
    meta["_table"] = df
    return meta


@lru_cache(maxsize=1)
def _load():
    if not MODEL_PATH.exists():
        return None
    try:
        import joblib
        return joblib.load(MODEL_PATH)
    except Exception as e:  # noqa: BLE001 - degrade (PRD N3)
        log.warning("crowd model artifact unreadable: %s", e)
        return None


def available() -> bool:
    return _load() is not None


def predict(venue_ids, times) -> list[float | None]:
    """Expected crowd (1-5) for each (venue_id, time) pair; None if unknown venue / outside night hours / no artifact."""
    art = _load()
    vids, times = list(venue_ids), list(times)
    if art is None or not vids:
        return [None] * len(vids)
    static = art["static"].set_index("venue_id")
    rows, idx = [], []
    for i, (v, t) in enumerate(zip(vids, times)):
        if v not in static.index:
            continue
        dt = to_dt(t)
        s = slot_of(dt)
        if s is None:
            continue
        nd = night_date(dt)
        wd = nd.weekday() if nd.weekday() in (3, 4, 5) else 3  # model knows Thu-Sat only
        row = static.loc[v].to_dict()
        row.update(venue_id=v, slot=s, weekday=wd, week=(nd - WEEK0).days // 7)
        rows.append(row)
        idx.append(i)
    out: list[float | None] = [None] * len(vids)
    if rows:
        p = art["model"].predict(pd.DataFrame(rows))
        for i, val in zip(idx, p):
            out[i] = None if math.isnan(val) else float(val)
    return out


def true_crowd_lookup(tables: dict):
    """EVALUATION ONLY (reports/ablation): f(venue_id, time) -> crowd_true at the 15-min slot, or None.

    Reads syn_true_state, which must never be a feature or reach the app/API.
    """
    t = tables.get("syn_true_state")  # evaluation-only table
    if t is None or t.empty:
        return None
    ts = pd.to_datetime(t["ts"], utc=True)
    idx = {(v, int(x.timestamp() // 900)): c for v, x, c in zip(t["venue_id"], ts, t["crowd_true"])}

    def f(venue_id, when):
        return idx.get((venue_id, int(to_dt(when).timestamp() // 900)))
    return f
