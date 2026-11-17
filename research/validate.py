"""Validate research datasets against research/survey/codebook.csv and the data rules.

Purpose
    Checks the synthetic (default) or real interview/survey CSVs: every codebook
    column present, types / ranges / allowed values, is_synthetic flag, ID
    prefixes, genres in the shared vocabulary, venue_ids in data/launch_venues.csv,
    quotes reference interviews, synthetic quote prefix. Also checks
    research/competitors.csv sourcing and scans research/** CSV/MD for PII.

Usage
    python -I research/validate.py            # synthetic CSVs in research/synthetic/
    python -I research/validate.py --real     # real CSVs in research/interviews/, research/survey/
    python -I research/validate.py --dir DIR  # synthetic CSVs in another folder

Exit code 0 = all checks pass; 1 = errors printed.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
CODEBOOK = RESEARCH / "survey" / "codebook.csv"
COMPETITORS = RESEARCH / "competitors.csv"
sys.path.insert(0, str(RESEARCH))
from gen_synthetic import load_genres, load_launch_venue_ids  # noqa: E402

SYN_FILES = {
    "syn_interviews": "syn_interviews.csv",
    "syn_interview_quotes": "syn_interview_quotes.csv",
    "syn_survey_responses": "syn_survey_responses.csv",
}
REAL_FILES = {
    "syn_interviews": RESEARCH / "interviews" / "interviews.csv",
    "syn_interview_quotes": RESEARCH / "interviews" / "quotes.csv",
    "syn_survey_responses": RESEARCH / "survey" / "responses.csv",
}
ID_PREFIX = {  # (synthetic, real)
    "interview_id": ("syn-int-", "int-r-"), "quote_id": ("syn-q-", "q-r-"),
    "response_id": ("syn-srv-", "srv-r-"),
}
COMPETITOR_COLS = [
    "competitor_id", "name", "category", "platform", "status", "last_seen_active",
    "realtime_signal", "crowd_sourced", "group_matching", "shows_confidence", "venue_tools",
    "nyc_coverage", "reporter_incentives", "consumer_price", "revenue_model",
    "why_failed_hypothesis", "source_url", "retrieved_at", "notes",
]
COMPETITOR_REQUIRED = ["competitor_id", "name", "category", "status", "last_seen_active",
                       "source_url", "retrieved_at"]
EMAIL_RE = re.compile(r"(?<![\w/])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?<![\w-])(\+?1[\s.-])?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?![\w-])")


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_codebook() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for row in read_csv(CODEBOOK):
        out.setdefault(row["dataset"], []).append(row)
    return out


def check_value(spec: dict, value: str, genres: set[str], venues: set[str]) -> str | None:
    """Return an error string, or None if `value` satisfies the codebook spec."""
    if value == "":
        return None if spec["nullable"] == "1" else "empty but not nullable"
    typ, allowed = spec["type"], spec["allowed_values"]
    if typ == "int":
        if not re.fullmatch(r"-?\d+", value):
            return f"not an int: {value!r}"
        v = int(value)
        if ".." in allowed:
            lo, hi = (int(x) for x in allowed.split(".."))
            return None if lo <= v <= hi else f"{v} outside {allowed}"
        return None if value in allowed.split(";") else f"{v} not in {allowed}"
    if typ == "enum":
        return None if value in allowed.split(";") else f"{value!r} not in allowed values"
    if typ == "multi_enum":
        items = value.split("|")
        if spec["column"] in ("favorite_genres",):
            ok = genres
        elif spec["column"] == "venue_mentions":
            ok = venues
        else:
            ok = set(allowed.split(";"))
        bad = [x for x in items if x not in ok]
        if "none" in items and len(items) > 1:
            return "'none' combined with other tools"
        return f"unknown values {bad}" if bad else None
    if typ == "date":
        try:
            dt.date.fromisoformat(value)
        except ValueError:
            return f"bad date {value!r}"
        return None
    if typ == "datetime":
        try:
            ts = dt.datetime.fromisoformat(value)
        except ValueError:
            return f"bad datetime {value!r}"
        return None if ts.tzinfo is not None else "datetime without offset"
    return None  # id / str checked elsewhere


def validate_dataset(name: str, rows: list[dict], specs: list[dict], real: bool,
                     genres: set[str], venues: set[str]) -> list[str]:
    errs: list[str] = []
    if not rows:
        return [f"{name}: no rows"]
    cols = set(rows[0])
    for spec in specs:
        if spec["column"] not in cols:
            errs.append(f"{name}: missing column {spec['column']}")
    extra = cols - {s["column"] for s in specs}
    if extra:
        errs.append(f"{name}: columns not in codebook {sorted(extra)}")
    flag = "0" if real else "1"
    seen_ids: set[str] = set()
    for i, row in enumerate(rows, start=2):
        if row.get("is_synthetic") != flag:
            errs.append(f"{name} line {i}: is_synthetic={row.get('is_synthetic')!r}, expected {flag}")
        for spec in specs:
            col = spec["column"]
            if col not in row:
                continue
            e = check_value(spec, row[col], genres, venues)
            if e:
                errs.append(f"{name} line {i} {col}: {e}")
            if col in ID_PREFIX and spec["type"] == "id":
                pre = ID_PREFIX[col][1 if real else 0]
                if not row[col].startswith(pre):
                    errs.append(f"{name} line {i} {col}: {row[col]!r} should start {pre!r}")
        pk = next(iter(row.values()))
        if pk in seen_ids:
            errs.append(f"{name} line {i}: duplicate id {pk}")
        seen_ids.add(pk)
        if name == "syn_interview_quotes" and not real and not row.get("text", "").startswith("[SYNTHETIC] "):
            errs.append(f"{name} line {i}: synthetic quote text must start '[SYNTHETIC] '")
        if name == "syn_survey_responses" and row.get("genre_no_pref") == "1" and row.get("favorite_genres"):
            errs.append(f"{name} line {i}: genre_no_pref=1 but favorite_genres set")
    return errs


def validate_competitors(path: Path = COMPETITORS) -> list[str]:
    if not path.exists():
        return [f"{path.relative_to(ROOT)} missing"]
    rows = read_csv(path)
    errs = []
    if len(rows) < 10:
        errs.append(f"competitors.csv has {len(rows)} rows (< 10)")
    if rows and list(rows[0]) != COMPETITOR_COLS:
        errs.append(f"competitors.csv columns differ from schema: {list(rows[0])}")
    for i, r in enumerate(rows, start=2):
        for c in COMPETITOR_REQUIRED:
            if not (r.get(c) or "").strip():
                errs.append(f"competitors.csv line {i}: empty {c}")
        if not re.match(r"https?://", r.get("source_url") or ""):
            errs.append(f"competitors.csv line {i}: source_url not http(s)")
        try:
            dt.date.fromisoformat(r.get("retrieved_at") or "")
        except ValueError:
            errs.append(f"competitors.csv line {i}: retrieved_at not YYYY-MM-DD")
        if r.get("status") not in {"live", "dead", "pivoted", "unknown"}:
            errs.append(f"competitors.csv line {i}: bad status {r.get('status')!r}")
        lsa = r.get("last_seen_active") or ""
        if lsa != "unknown" and not re.fullmatch(r"\d{4}-\d{2}", lsa):
            errs.append(f"competitors.csv line {i}: last_seen_active must be YYYY-MM or unknown")
        if r.get("status") in {"dead", "pivoted"} and not (r.get("why_failed_hypothesis") or "").startswith("Hypothesis"):
            errs.append(f"competitors.csv line {i}: dead/pivoted row needs 'Hypothesis: ...'")
    return errs


def scan_pii(root: Path = RESEARCH) -> list[str]:
    errs = []
    for p in sorted(root.rglob("*")):
        if p.suffix.lower() not in {".csv", ".md"} or "tests" in p.parts:
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
            if EMAIL_RE.search(line):
                errs.append(f"PII? email-like text in {p.relative_to(ROOT)}:{n}")
            if PHONE_RE.search(line):
                errs.append(f"PII? phone-like text in {p.relative_to(ROOT)}:{n}")
    return errs


def run(real: bool = False, data_dir: Path | None = None) -> list[str]:
    codebook = load_codebook()
    genres, venues = set(load_genres()), set(load_launch_venue_ids())
    errs: list[str] = []
    tables: dict[str, list[dict]] = {}
    for name in SYN_FILES:
        path = REAL_FILES[name] if real else (data_dir or RESEARCH / "synthetic") / SYN_FILES[name]
        if not path.exists():
            errs.append(f"{name}: file missing {path}")
            continue
        tables[name] = read_csv(path)
        errs += validate_dataset(name, tables[name], codebook[name], real, genres, venues)
    if "syn_interviews" in tables and "syn_interview_quotes" in tables:
        ids = {r["interview_id"] for r in tables["syn_interviews"]}
        for q in tables["syn_interview_quotes"]:
            if q["interview_id"] not in ids:
                errs.append(f"quote {q['quote_id']}: unknown interview_id {q['interview_id']}")
    errs += validate_competitors()
    errs += scan_pii()
    return errs


def main() -> None:
    ap = argparse.ArgumentParser(description="Validate research datasets")
    ap.add_argument("--real", action="store_true", help="validate real CSVs (is_synthetic=0)")
    ap.add_argument("--dir", type=Path, default=None, help="folder holding synthetic CSVs")
    args = ap.parse_args()
    errs = run(args.real, args.dir)
    for e in errs:
        print("ERROR", e)
    print(f"{'FAIL' if errs else 'OK'}: {len(errs)} error(s)")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
