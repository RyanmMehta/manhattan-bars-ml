"""Argument parsing for `python -I -m simulator` (see __main__.py)."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from .config import DEMO_NOW, LIVE_SIM_DB


def _read_csvs(csv_dir: Path) -> dict[str, pd.DataFrame]:
    from . import schema
    out = {}
    for n in schema.TABLES:
        p = csv_dir / f"{n}.csv"
        if p.exists():
            out[n] = pd.read_csv(p, dtype={"venue_id": str, "home_venue_id": str, "as_of_date": str},
                                 keep_default_na=True)
    return out


def cmd_replay(a) -> int:
    from . import replay, timeutil
    tables = _read_csvs(Path(a.csv_dir))
    if a.shift_to:
        sh = replay.shift(tables, date.fromisoformat(a.shift_to))
        from .io import to_output, write_csv
        d = Path(a.csv_dir) / "shifted"
        for k, df in sh.items():
            write_csv(to_output(df, k), d / f"{k}.csv")
        print(f"shifted demo night to {a.shift_to}: {', '.join(f'{k}={len(v)}' for k, v in sh.items())} -> {d}")
        return 0
    seen = replay.visible(tables, a.now)
    states, source = replay.live_states(seen, a.now)
    now = timeutil.parse_ts(a.now)
    names = pd.read_csv(Path(__file__).parent / "data" / "venue_inputs.csv", dtype=str).set_index("license_id")["name"]
    attrs = seen["syn_venue_attributes"].set_index("venue_id")
    upd = seen["syn_venue_updates"]
    offers = upd[upd["offer"].notna()].groupby("venue_id")["offer"].last()
    ob = seen["open_bounties"].set_index("venue_id")["points"]
    rep = seen["syn_scout_reports"]
    print(f"now={a.now}  (state source: {source}; ALL DATA SYNTHETIC)")
    print(f"{'venue':30} {'style':14} {'rep180':>6} {'fresh':>5} {'vibe':>4} {'conf':>5} {'trend':8} bounty offer")
    for s in sorted(states, key=lambda x: (x["vibe_score"] is None, -(x["vibe_score"] or 0))):
        v = s["venue_id"]
        if a.venue and v != a.venue:
            continue
        n180 = int(((rep["venue_id"] == v) & (rep["ts"] >= now - pd.Timedelta(minutes=180))).sum())
        print(f"{str(names.get(v, v))[:30]:30} {attrs.at[v, 'style']:14} {n180:6d} "
              f"{'' if s['freshness_minutes'] is None else s['freshness_minutes']:>5} "
              f"{'' if s['vibe_score'] is None else s['vibe_score']:>4} "
              f"{'' if s['confidence'] is None else s['confidence']:>5} {str(s['trend'] or ''):8} "
              f"{ob.get(v, ''):>6} {offers.get(v, '')}")
    st = rep[rep["ts"] >= now - pd.Timedelta(minutes=180)]["status"].value_counts().to_dict()
    print(f"open bounties: {len(seen['open_bounties'])}; report status (last 180 min): {st}")
    if a.venue:
        r = rep[rep["venue_id"] == a.venue].tail(10)
        print(r[["report_id", "scout_id", "ts", "crowd", "dancing", "line_minutes", "status"]].to_string(index=False))
    return 0


def cmd_validate(a) -> int:
    from . import validate
    from .config import load
    tables = _read_csvs(Path(a.csv_dir))
    m = json.loads((Path(a.csv_dir) / "manifest.json").read_text()) if (Path(a.csv_dir) / "manifest.json").exists() else {}
    rep = validate.run(tables, load(m.get("preset", "default"), seed=m.get("seed", 42), nights=m.get("nights")))
    validate.write(rep, Path(a.csv_dir))
    for c in rep["checks"]:
        print(f"{'SKIP' if c['ok'] is None else 'ok  ' if c['ok'] else 'FAIL'} {c['check']}  {c['value']}")
    return 0 if rep["ok"] else 1


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    argv = list(sys.argv[1:] if argv is None else argv)
    sub = argv[0] if argv and argv[0] in ("extract-inputs", "validate", "replay", "build") else None
    if sub:
        argv = argv[1:]
    p = argparse.ArgumentParser(prog="python -I -m simulator", description="live-sim synthetic nightlife simulator")
    p.add_argument("--csv-dir", default="data/synthetic_live")
    if sub in (None, "build"):
        p.add_argument("--seed", type=int, default=42)
        p.add_argument("--out", default=LIVE_SIM_DB)
        p.add_argument("--nights", type=int, default=None, help="quick mode: last N nights (ends Sat Nov 14)")
        p.add_argument("--preset", default="default", choices=["default", "small", "demo"])
        p.add_argument("--strict", action="store_true", help="exit 1 on any failed validation check")
    if sub == "replay":
        p.add_argument("--now", default=DEMO_NOW)
        p.add_argument("--venue", default=None)
        p.add_argument("--shift-to", default=None)
    a = p.parse_args(argv)
    if sub == "extract-inputs":
        from .extract import extract
        print(f"wrote {len(extract())} venues to simulator/data/venue_inputs.csv")
        return 0
    if sub == "validate":
        return cmd_validate(a)
    if sub == "replay":
        return cmd_replay(a)
    from .build import build
    r = build(seed=a.seed, out=a.out, nights=a.nights, preset=a.preset, csv_dir=a.csv_dir)
    m = r["manifest"]
    print(f"live-sim: {m['nights']} nights, seed {m['seed']}, {m['build_seconds']}s -> {a.out} (ALL ROWS SYNTHETIC)")
    for k, v in m["rows"].items():
        print(f"  {k:32} {v:>8}")
    print(f"validation: {'OK' if r['validation']['ok'] else 'FAILED ' + ', '.join(r['validation']['failed'])}")
    if r["hard_fail"] or (a.strict and not r["validation"]["ok"]):
        return 1
    return 0
