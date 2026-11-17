"""k-means venue-style clustering on REAL public `venue_features` (v_bars, ~1.7k venues). Not synthetic.

fit() -> sweeps k=3..8 (seed 42), picks max silhouette unless a cluster < 3% of venues, labels clusters from
their top z-scored features, writes recs/artifacts/clusters.csv + clusters.json.
assignments() / label_for(venue_id) read the artifact (lazy, cached). Labels describe public-data profile
(licence, inspections, OSM, density) only; they are not quality or vibe.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .config import SEED

ART = Path(__file__).resolve().parent / "artifacts"
CSV = ART / "clusters.csv"
META = ART / "clusters.json"
TARGETS = ["noise_complaints", "high_noise"]  # complaint targets are never clustering inputs
K_RANGE = range(3, 9)
MIN_SHARE = 0.03

PHRASE = {  # feature: (phrase when above average, phrase when below)
    "density_250m": ("dense nightlife block", "quieter block"), "density_100m": ("packed street", "spread-out street"),
    "years_licensed": ("long-established", "newly licensed"), "osm_closes_late": ("late-closing", "early-closing"),
    "osm_outdoor_seating": ("outdoor seating", "indoor-only"), "osm_has_website": ("web presence", "no web presence"),
    "n_inspections": ("frequently inspected", "rarely inspected"), "mean_score": ("weaker inspections", "clean inspections"),
    "n_violations": ("more violations", "few violations"), "n_critical_violations": ("critical violations", "few critical violations"),
    "has_pest_violation": ("pest history", "no pest history"), "dohmh_matched": ("serves food", "drinks-only"),
    "n_additional_bars": ("multi-bar", "single bar"),
}
CAT_FMT = {"latest_grade": "grade {}", "cuisine": "{} food", "osm_amenity": "OSM {}", "venue_type": "{}",
           "neighborhood": "{}", "liquor_tier": "{}"}
SKIP_VALUES = {"Not matched", "not_listed", "none", "None", "Unknown", "unknown"}


def _prep(df: pd.DataFrame, with_geo: bool):
    from sklearn.compose import ColumnTransformer
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.impute import SimpleImputer

    X = df.drop(columns=["license_id"] + [t for t in TARGETS if t in df.columns])
    if not with_geo:
        X = X.drop(columns=["lat", "lon"])
    cats = [c for c in X.columns if X[c].dtype == object or str(X[c].dtype).startswith(("str", "string", "category"))]
    nums = [c for c in X.columns if c not in cats]
    ct = ColumnTransformer([
        ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), nums),
        ("cat", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=20, sparse_output=False), cats),
    ])
    return X, ct, nums, cats


def _label(df: pd.DataFrame, labels: np.ndarray, nums, cats) -> dict[int, str]:
    z = (df[nums] - df[nums].mean()) / df[nums].std(ddof=0).replace(0, 1)
    out = {}
    for k in sorted(set(labels)):
        m = labels == k
        zs = z[m].mean().sort_values(key=lambda s: -s.abs())
        parts = []
        for f, val in zs.items():
            if f not in PHRASE or abs(val) < 0.3:
                continue
            parts.append(PHRASE[f][0] if val > 0 else PHRASE[f][1])
            if len(parts) == 2:
                break
        # most over-represented category
        best, lift = None, 1.3
        for c in cats:
            share_all = df[c].value_counts(normalize=True)
            share_k = df.loc[m, c].value_counts(normalize=True)
            for val, s in share_k.items():
                if str(val) in SKIP_VALUES:
                    continue
                if s >= 0.4 and s / share_all[val] > lift:
                    best, lift = CAT_FMT.get(c, "{}").format(str(val).replace("_", " ") if c == "latest_grade" else str(val).replace("_", " ").lower()), s / share_all[val]
        if best:
            parts.append(best)
        out[int(k)] = ", ".join(parts) if parts else "typical bar"
    # make labels unique
    seen: dict[str, int] = {}
    for k, v in out.items():
        seen[v] = seen.get(v, 0) + 1
        if seen[v] > 1:
            out[k] = f"{v} ({seen[v]})"
    return out


def fit(with_geo: bool = False, write: bool = True) -> dict:
    """Run the sweep; returns metadata (k, silhouette per k, profiles)."""
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from . import data

    df = data.venue_features(bars_only=True).reset_index(drop=True)
    X, ct, nums, cats = _prep(df, with_geo)
    Z = ct.fit_transform(X)
    sweep = []
    for k in K_RANGE:
        km = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit(Z)
        sil = float(silhouette_score(Z, km.labels_, random_state=SEED, sample_size=min(len(Z), 2000)))
        min_share = float(np.bincount(km.labels_).min() / len(Z))
        sweep.append({"k": k, "inertia": float(km.inertia_), "silhouette": sil, "min_share": min_share, "_km": km})
    ok = [s for s in sweep if s["min_share"] >= MIN_SHARE] or sweep
    best = max(ok, key=lambda s: s["silhouette"])
    km = best["_km"]
    labels = km.labels_
    names = _label(df, labels, nums, cats)
    df["cluster_id"] = labels
    df["cluster_label"] = [names[int(c)] for c in labels]
    prof = df.groupby("cluster_id").agg(n=("license_id", "size"), **{f"mean_{c}": (c, "mean") for c in nums})
    for c in cats:
        prof[f"mode_{c}"] = df.groupby("cluster_id")[c].agg(lambda s: s.mode().iat[0])
    prof["cluster_label"] = [names[int(i)] for i in prof.index]
    meta = {
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_source": "data/manhattan_bars.db venue_features JOIN v_bars (real public data)",
        "rows": int(len(df)), "with_geo": with_geo, "k": int(best["k"]), "seed": SEED,
        "sweep": [{k: v for k, v in s.items() if k != "_km"} for s in sweep],
        "labels": {str(k): v for k, v in names.items()}, "is_synthetic": False,
        "profiles": json.loads(prof.reset_index().round(3).to_json(orient="records")),
    }
    if write:
        ART.mkdir(exist_ok=True)
        df.rename(columns={"license_id": "venue_id"})[["venue_id", "cluster_id", "cluster_label"]].to_csv(CSV, index=False)
        META.write_text(json.dumps(meta, indent=1))
        _cached.cache_clear()
    meta["_df"] = df
    meta["_profiles"] = prof
    return meta


@lru_cache(maxsize=1)
def _cached() -> pd.DataFrame | None:
    if not CSV.exists():
        return None
    return pd.read_csv(CSV)


def assignments() -> pd.DataFrame:
    """DataFrame[venue_id, cluster_id, cluster_label] (empty if the artifact is missing)."""
    df = _cached()
    return pd.DataFrame(columns=["venue_id", "cluster_id", "cluster_label"]) if df is None else df.copy()


@lru_cache(maxsize=1)
def _index() -> dict:
    df = _cached()
    return {} if df is None else {r.venue_id: (int(r.cluster_id), r.cluster_label) for r in df.itertuples()}


def label_for(venue_id) -> str | None:
    v = _index().get(venue_id)
    return None if v is None else v[1]


def cluster_for(venue_id) -> int | None:
    v = _index().get(venue_id)
    return None if v is None else v[0]
