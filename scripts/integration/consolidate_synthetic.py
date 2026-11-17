"""Generate root SYNTHETIC_DATA.md from every docs/synthetic/*.md registry.

Usage: python -I scripts/integration/consolidate_synthetic.py [--out SYNTHETIC_DATA.md]

Never edit the generated sections of SYNTHETIC_DATA.md by hand; fix the source registry.
Tables in each registry are copied as-is under the owner's heading; markdown tables whose
header mentions dataset/file/table are also collected into the master index.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

INTRO = """# Synthetic data in this repo

> **Generated** by `scripts/integration/consolidate_synthetic.py` (`make synthetic-docs`) from
> every `docs/synthetic/<workstream>.md`. Edit those files, not this one.

Nightlife Autopilot has **no real live data yet**. Everything about "tonight" (scout reports,
venue updates, crowds, users, points, bounties, owner analytics, interview data) is
**synthetic**, generated deterministically (seed 42) for the Nov 17 class demo. The only real
data is the public-data pipeline: NY SLA licences, NYC DOHMH inspections, NYC 311 noise
complaints and OpenStreetMap (`data/manhattan_bars.db`, `data/launch_venues*.csv`).

How to spot it (CONTRACTS.md "Synthetic data rule"):
1. every synthetic table/CSV has `is_synthetic = 1`;
2. synthetic files live under a path containing `synthetic`; synthetic DB tables start with `syn_`;
   synthetic primary keys start with `syn-`;
3. code that reads synthetic data is marked `# SYNTHETIC: <real source>` / `// SYNTHETIC:`;
4. the UI shows a **demo data** badge wherever synthetic data is shown.

## The global swap switch (step 1 of every swap)

Every app table has a real twin without the `syn_` prefix (`scout_reports`, `venue_updates`,
`venue_events`, `feedback`, `bounties`, `disputes`, `points_ledger`), created empty by the
backend from day one. The backend reads `syn_x UNION ALL x`.

1. Start writing real rows into the un-prefixed twin (the app's POST endpoints already do).
2. When the real table has enough data, set `INCLUDE_SYNTHETIC=0` on the backend (Render env).
   `/api/health` then reports `"data": "real"` and lists return `X-Data: real`.
3. Stop running `python -I -m simulator --seed 42 --out data/live_sim.db` in the build and unset
   `DEMO_NOW` / `VITE_DEMO_NOW` so the app uses the wall clock.
4. Remove the dataset's `SYNTHETIC:` code paths listed below and its row in the owner's registry.

Checked by `tests/contract/test_isolation.py::test_include_synthetic_off`.

## Evaluation-only tables (never swapped into the app)

`syn_true_state` and `syn_scout_truth` are the simulator's hidden ground truth. They are read
only by evaluation/test code, never by `backend/`, `recs/` runtime or model features
(checked by `tests/contract/test_isolation.py`). With real data they simply disappear;
evaluation then uses post-visit feedback and audits instead.
"""


def git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def grep_counts() -> Counter:
    counts: Counter = Counter()
    skip = {".git", "node_modules", "dist", ".venv", "__pycache__"}
    for f in ROOT.rglob("*"):
        if not f.is_file() or skip & set(f.parts) or f.suffix not in {".py", ".ts", ".tsx", ".js", ".jsx", ".sql", ".sh", ".mjs", ".cjs", ".yaml", ".yml"}:
            continue
        try:
            n = sum(1 for line in f.read_text(errors="ignore").splitlines() if re.search(r"(#|//|--)\s*SYNTHETIC:", line))
        except OSError:
            continue
        if n:
            counts[f.relative_to(ROOT).parts[0]] += n
    return counts


def demote(md: str) -> str:
    """Shift headings down two levels so each registry nests under its owner heading."""
    out = []
    in_code = False
    for line in md.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        if not in_code and re.match(r"^#{1,4} ", line):
            line = "##" + line
        out.append(line)
    return "\n".join(out).strip()


def tables(md: str):
    """Yield (header_cells, rows) for each markdown table."""
    lines = md.splitlines()
    i = 0
    while i < len(lines) - 1:
        if lines[i].lstrip().startswith("|") and re.match(r"^\s*\|?\s*:?-{3,}", lines[i + 1]):
            head = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            yield head, rows
            i = j
        else:
            i += 1


def master_rows(name: str, md: str):
    keys = {"dataset": ("dataset", "file", "table", "name"), "imitates": ("imitat",),
            "generated": ("generat", "how"), "real": ("real",), "swap": ("swap",)}
    for head, rows in tables(md):
        low = [h.lower() for h in head]
        if not any(any(k in h for k in keys["dataset"]) for h in low):
            continue
        if not any("real" in h or "imitat" in h for h in low):
            continue
        idx = {}
        for k, pats in keys.items():
            for n, h in enumerate(low):
                if any(p in h for p in pats) and n not in idx.values():
                    idx[k] = n
                    break
        for r in rows:
            get = lambda k: (r[idx[k]] if k in idx and idx[k] < len(r) else "")  # noqa: E731
            yield [name, get("dataset"), get("imitates"), get("real"), get("swap")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "SYNTHETIC_DATA.md")
    a = ap.parse_args()
    regs = sorted((ROOT / "docs/synthetic").glob("*.md"))
    parts = [INTRO]
    master = []
    for f in regs:
        master += list(master_rows(f.stem, f.read_text()))
    parts.append("## Master index\n")
    if master:
        parts.append("| owner | dataset (file/table) | imitates | real replacement | swap steps |\n|---|---|---|---|---|")
        parts += ["| " + " | ".join(c.replace("\n", " ") for c in r) + " |" for r in master]
    else:
        parts.append("_No registries merged yet._")
    pipeline = ROOT / "data/synthetic"
    parts.append("\n### Pre-existing public-pipeline synthetic data\n\n"
                 "`data/synthetic/*` and the `synthetic_{independent,copula,cart}_10000` tables in "
                 "`data/manhattan_bars.db` are synthetic *training* rows from `src/simulate.py` "
                 "(see README §3). They imitate `venue_features` and are not used by the app."
                 + ("" if pipeline.exists() else " (folder not present)"))
    parts.append("\n## Per-workstream registries\n")
    for f in regs:
        parts.append(f"### {f.stem}  (`docs/synthetic/{f.name}`)\n\n{demote(f.read_text())}\n")
    counts = grep_counts()
    parts.append("## `SYNTHETIC:` code markers\n\n| folder | count |\n|---|---|")
    parts += [f"| `{k}/` | {v} |" for k, v in sorted(counts.items())]
    parts.append(f"| **total** | **{sum(counts.values())}** |\n")
    parts.append(f"_Generated from {len(regs)} registries at commit `{git_sha()}`._\n")
    a.out.write_text("\n".join(parts))
    print(f"wrote {a.out} ({len(regs)} registries, {len(master)} indexed datasets, "
          f"{sum(counts.values())} SYNTHETIC markers)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
