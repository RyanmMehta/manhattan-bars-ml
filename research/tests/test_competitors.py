"""research/competitors.csv is real desk research: every row sourced and dated."""
import csv
import datetime as dt
from pathlib import Path

import validate as v

PATH = Path(__file__).resolve().parents[1] / "competitors.csv"
MUST_HAVE = ["barhop", "buzzd", "nytevibe", "what's playin", "barhopper", "google maps",
             "instagram", "partiful", "resy", "dice"]


def rows():
    return list(csv.DictReader(PATH.open(encoding="utf-8")))


def test_validator_clean():
    assert v.validate_competitors() == []


def test_required_competitors_present():
    names = " ".join(r["name"].lower() for r in rows())
    missing = [m for m in MUST_HAVE if m not in names]
    assert not missing, missing
    assert len(rows()) >= 12


def test_sourced_and_recent():
    for r in rows():
        assert r["source_url"].startswith(("http://", "https://"))
        d = dt.date.fromisoformat(r["retrieved_at"])
        assert dt.date(2026, 11, 10) <= d <= dt.date(2026, 11, 24), "re-check within 7 days of demo"
        assert not ("synthetic" in r["notes"].lower() and "not synthetic" not in r["notes"].lower())
