"""Tableau extract: hourly_by_style.csv (style x weekday x local hour) from the app-visible reports.

# SYNTHETIC: aggregates of synthetic reports; replace with the same query over real scout_reports.
"""
from __future__ import annotations

import pandas as pd

from . import timeutil

DAY = {3: "Thu", 4: "Fri", 5: "Sat"}


def hourly_by_style(reports: pd.DataFrame, attrs: pd.DataFrame) -> pd.DataFrame:
    r = reports[reports["status"].isin(["accepted", "disputed"])].copy()
    r["style"] = r["venue_id"].map(attrs.set_index("venue_id")["style"])
    r["weekday"] = r["ts"].map(lambda x: DAY[timeutil.night_of(x).weekday()])
    r["hour"] = (pd.Series(timeutil.local_hour(r["ts"]), index=r.index) // 1 % 24).astype(int)
    g = r.groupby(["style", "weekday", "hour"], sort=True)
    out = g.agg(n_reports=("report_id", "size"), mean_crowd=("crowd", "mean"), mean_dancing=("dancing", "mean"),
                mean_line_minutes=("line_minutes", "mean"), n_venues=("venue_id", "nunique")).reset_index()
    out["is_synthetic"] = 1
    return out
