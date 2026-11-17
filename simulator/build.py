"""The fixed build (CONTRACTS v2.2 §J): generate -> CSVs + snapshots + extracts -> validate -> load DB -> manifest."""
from __future__ import annotations

import logging
import time
from pathlib import Path

from . import extracts, generate, io, load, schema, snapshots, validate
from .config import load as load_cfg

log = logging.getLogger("simulator")
HARD = ("schema:", "fk:", "genres", "all_rows_is_synthetic", "verified_iff", "ledger_sums", "no_reports_after")


def build(seed: int = 42, out: str = "data/live_sim.db", nights: int | None = None, preset: str = "default",
          csv_dir: str = "data/synthetic_live") -> dict:
    """Run the whole pipeline; returns {'manifest', 'validation', 'hard_fail'}."""
    t0 = time.perf_counter()
    csv_dir_p = Path(csv_dir)
    if "synthetic" not in str(csv_dir_p.resolve()):
        raise ValueError("CSV output folder must contain 'synthetic' in its path (synthetic-data rule)")
    load.check_target(Path(out))
    cfg = load_cfg(preset, seed=seed, nights=nights)
    tables = generate(cfg)
    meta = tables.pop("_meta").iloc[0].to_dict()
    outputs = {n: io.to_output(tables[n], n) for n in schema.TABLES}
    snaps, source = snapshots.build({k: tables[k] for k in ("syn_venue_attributes", "syn_scout_reports",
                                                            "syn_venue_updates", "syn_disputes", "syn_bounties",
                                                            "syn_scout_reputation_history", "syn_scouts")})
    files = {}
    for n, df in outputs.items():
        files[f"{n}.csv"] = csv_dir_p / f"{n}.csv"
        io.write_csv(df, files[f"{n}.csv"])
    snap_out = io.to_output(snaps, "demo_night_snapshots")
    files["demo_night_snapshots.csv"] = csv_dir_p / "demo_night_snapshots.csv"
    io.write_csv(snap_out, files["demo_night_snapshots.csv"])
    hx = extracts.hourly_by_style(tables["syn_scout_reports"], tables["syn_venue_attributes"])
    files["extracts/hourly_by_style.csv"] = csv_dir_p / "extracts" / "hourly_by_style.csv"
    io.write_csv(hx, files["extracts/hourly_by_style.csv"])
    counts = load.load(outputs, Path(out))
    build_s = round(time.perf_counter() - t0, 2)
    csv_bytes = sum(p.stat().st_size for p in files.values())
    vin = dict(outputs)
    vin["syn_feedback"] = outputs["syn_feedback"].assign(_fit=tables["syn_feedback"]["_fit"].to_numpy())
    vin["syn_true_state"] = outputs["syn_true_state"].assign(_open=tables["syn_true_state"]["_open"].to_numpy())
    report = validate.run(vin, cfg, {"csv_bytes": csv_bytes, "build_seconds": build_s})
    report["build_seconds"] = build_s
    validate.write(report, csv_dir_p)
    hard = [c for c in report["failed"] if c.startswith(HARD)]
    rows = {**{n: len(df) for n, df in outputs.items()}, "demo_night_snapshots": len(snap_out)}
    manifest = io.write_manifest(csv_dir_p, cfg, files, rows, {
        "nights": meta["nights"], "rate_limited_dropped": int(meta["rate_limited_dropped"]),
        "snapshot_source": source, "build_seconds": build_s, "db": str(out), "db_rows": counts,
        "validation_ok": report["ok"], "validation_failed": report["failed"], "preset": preset})
    log.info("build done in %.1fs; validation ok=%s failed=%s", build_s, report["ok"], report["failed"])
    return {"manifest": manifest, "validation": report, "hard_fail": hard}
