"""Aggregate research interview/survey CSVs into research/<source>/summary_tables.csv.

Purpose
    Tidy aggregates (metric, segment, value, n, is_synthetic) for tableau's
    "voice of customer" dashboard and for research/summary.md. With
    --source synthetic every number is DEMO DATA, not a finding.

Usage
    python -I research/analysis.py --source synthetic   # -> research/synthetic/summary_tables.csv
    python -I research/analysis.py --source real        # -> research/survey/summary_tables.csv

Output columns: metric, segment, value, n, is_synthetic
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "research"
SOURCES = {
    # SYNTHETIC: placeholder inputs; --source real reads the real exports instead.
    "synthetic": (R / "synthetic" / "syn_survey_responses.csv", R / "synthetic" / "syn_interviews.csv",
                  R / "synthetic" / "summary_tables.csv"),
    "real": (R / "survey" / "responses.csv", R / "interviews" / "interviews.csv",
             R / "survey" / "summary_tables.csv"),
}
FACTORS = ["genres", "want_dancing", "crowd_pref", "max_cover_usd", "max_line_minutes",
           "max_distance_km", "price", "friends_there"]


def survey_metrics(s: pd.DataFrame, seg: str) -> list[tuple]:
    n = len(s)
    out = [
        ("pct_bad_pick_last_month", seg, s.bad_pick_last_month.mean() * 100, n),
        ("median_decision_minutes", seg, s.decision_minutes.median(), n),
        ("median_nights_out_per_month", seg, s.nights_out_per_month.median(), n),
        ("median_freshness_tolerance_min", seg, s.freshness_tolerance_min.median(), n),
        ("pct_freshness_tolerance_le_60", seg, (s.freshness_tolerance_min <= 60).mean() * 100, n),
        ("pct_would_use_weekly", seg, s.would_use_weekly.mean() * 100, n),
        ("pct_would_scout_yes_or_already", seg, (s.would_scout >= 2).mean() * 100, n),
        ("pct_scout_ge1_report_per_night", seg, ((s.would_scout >= 1) & (s.reports_per_night_if_scout >= 1)).mean() * 100, n),
        ("nps_concept", seg, ((s.nps_concept >= 9).mean() - (s.nps_concept <= 6).mean()) * 100, n),
        ("pct_planner_is_one_person", seg, s.who_picks.isin(["me", "friend"]).mean() * 100, n),
        ("pct_use_2plus_tools", seg, (s.current_tools.str.count(r"\|") >= 1).mean() * 100, n),
    ]
    for f in FACTORS:
        out.append((f"mean_importance_{f}", seg, s[f"importance_{f}"].mean(), n))
    ranks = pd.Series({f: s[f"importance_{f}"].mean() for f in FACTORS}).rank(ascending=False, method="min")
    out += [(f"rank_importance_{f}", seg, ranks[f], n) for f in FACTORS]
    for col in ("trust_cue_pref", "points_value_pref"):
        for k, v in s[col].value_counts(normalize=True).sort_index().items():
            out.append((f"pct_{col}_{k}", seg, v * 100, n))
    tools = s.current_tools.str.split("|").explode()
    for k, v in (tools.value_counts().sort_index() / n).items():
        out.append((f"pct_use_tool_{k}", seg, v * 100, n))
    return out


def interview_metrics(iv: pd.DataFrame) -> list[tuple]:
    out = [(f"n_interviews_{k}", "interviews", v, v) for k, v in iv.segment.value_counts().sort_index().items()]
    op = iv[iv.segment == "operator"]
    if len(op):
        w = pd.to_numeric(op.operator_wtp_usd_month)
        out += [("operator_median_wtp_usd_month", "operators", w.median(), len(op)),
                ("operators_wtp_ge_49", "operators", int((w >= 49).sum()), len(op))]
    cons = iv[iv.segment != "operator"]
    if len(cons):
        top = pd.concat([cons.top_factor_1, cons.top_factor_2, cons.top_factor_3])
        out += [(f"top3_mentions_{k}", "consumers+scouts", v, len(cons)) for k, v in top.value_counts().sort_index().items()]
    out.append(("mean_concept_reaction", "interviews", iv.concept_reaction.mean(), len(iv)))
    return out


def build(source: str) -> list[dict]:
    survey_p, iv_p, _ = SOURCES[source]
    s, iv = pd.read_csv(survey_p), pd.read_csv(iv_p)
    flag = int(s.is_synthetic.max() == 1 or iv.is_synthetic.max() == 1)
    rows = survey_metrics(s, "all")
    for st, lab in ((1, "students"), (0, "non_students")):
        rows += survey_metrics(s[s.student == st], lab)
    rows += interview_metrics(iv)
    return [{"metric": m, "segment": seg, "value": round(float(v), 2), "n": int(n), "is_synthetic": flag}
            for m, seg, v, n in rows]


def main() -> None:
    ap = argparse.ArgumentParser(description="Aggregate research data")
    ap.add_argument("--source", choices=list(SOURCES), default="synthetic")
    args = ap.parse_args()
    rows = build(args.source)
    out = SOURCES[args.source][2]
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader(); w.writerows(rows)
    print(f"wrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
