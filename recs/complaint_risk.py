"""311 noise-complaint risk for venues (REAL public data; not synthetic).

Always labelled "311 noise-complaint risk". It is the predicted probability that a venue has >= 3 noise
complaints in 3 years (`high_noise` in venue_features), from licence/inspection/OSM/density features. It is NOT a
measure of quality, popularity or vibe and never feeds match_score, rank_score, vibe_score, reasons or routing.

train() -> HistGradientBoostingClassifier, same setup as src/evaluate.py; out-of-fold scores (5-fold) for every
venue so a venue's own label never scores itself; writes recs/artifacts/complaint_risk.csv + .json.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import pandas as pd

from .config import SEED

LABEL = "311 noise-complaint risk"
ART = Path(__file__).resolve().parent / "artifacts"
CSV = ART / "complaint_risk.csv"
META = ART / "complaint_risk.json"
TARGETS = ["noise_complaints", "high_noise"]


def train(write: bool = True) -> dict:
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import average_precision_score, roc_auc_score
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import OneHotEncoder

    from . import data

    df = data.venue_features(bars_only=False).reset_index(drop=True)
    X = df.drop(columns=["license_id", *TARGETS])
    y = df["high_noise"].astype(int)
    cats = [c for c in X.columns if not pd.api.types.is_numeric_dtype(X[c])]
    nums = [c for c in X.columns if c not in cats]
    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=5, sparse_output=False), cats),
                             ("num", "passthrough", nums)])
    pipe = make_pipeline(pre, HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, random_state=SEED))
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    p = cross_val_predict(pipe, X, y, cv=cv, method="predict_proba")[:, 1]
    out = pd.DataFrame({"venue_id": df["license_id"], "complaint_risk": p.round(4)})
    meta = {
        "label": LABEL, "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_source": "data/manhattan_bars.db venue_features (real public data)", "rows": int(len(df)),
        "target": "high_noise (>= 3 noise complaints in 3 yrs)", "base_rate": float(y.mean()),
        "oof_roc_auc": float(roc_auc_score(y, p)), "oof_pr_auc": float(average_precision_score(y, p)),
        "is_synthetic": False,
        "note": "Not a quality, popularity or vibe signal. Shown only as the separate complaint_risk field.",
    }
    if write:
        ART.mkdir(exist_ok=True)
        out.to_csv(CSV, index=False)
        META.write_text(json.dumps(meta, indent=1))
        _index.cache_clear()
    return meta


@lru_cache(maxsize=1)
def _index() -> dict:
    if not CSV.exists():
        return {}
    df = pd.read_csv(CSV)
    return dict(zip(df["venue_id"], df["complaint_risk"]))


def scores() -> dict:
    """{venue_id: probability in [0, 1]} (empty if the artifact is missing)."""
    return dict(_index())


def score_for(venue_id) -> float | None:
    v = _index().get(venue_id)
    return None if v is None else float(v)
