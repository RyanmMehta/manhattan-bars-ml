"""Ownership audit: which paths each nightlife/* branch changed outside its owned folders.

Usage: python -I scripts/integration/ownership_audit.py [--base origin/nightlife/contracts] [--out docs/workstreams/ownership_audit.md]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMON = ["docs/prd/{n}/", "docs/workstreams/{n}.md", "docs/synthetic/{n}.md"]
OWNED = {
    "specs": ["docs/specs/"],
    "research": ["research/"],
    "tableau": ["analytics/tableau/"],
    "live-sim": ["simulator/", "data/synthetic_live/"],
    "ml-recs": ["recs/"],
    "backend": ["backend/"],
    "frontend": ["frontend/"],
    "coursework": ["coursework/"],
    "integration": ["tests/", "scripts/", "Makefile", ".github/", "README.md", "SYNTHETIC_DATA.md", "DEMO.md",
                    "CONTRIBUTING.md", "render.yaml", ".dockerignore", ".gitignore", "requirements-dev.txt",
                    "data/launch_venues_full.csv", "vercel.json"],
}


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def changed(base: str, branch: str) -> list[str]:
    mb = git("merge-base", base, branch).strip()
    return [p for p in git("diff", "--name-only", mb, branch).splitlines() if p]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="origin/nightlife/contracts")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("branches", nargs="*", default=list(OWNED))
    a = ap.parse_args()
    lines = ["# Ownership audit", "", f"Base: `{a.base}`", "",
             "| branch | files changed | outside owned folders |", "|---|---|---|"]
    detail = []
    for n in a.branches:
        ref = f"origin/nightlife/{n}"
        try:
            paths = changed(a.base, ref)
        except subprocess.CalledProcessError:
            lines.append(f"| {n} | (branch missing) | |")
            continue
        own = OWNED.get(n, []) + [c.format(n=n) for c in COMMON]
        bad = [p for p in paths if not any(p == o or p.startswith(o) for o in own)]
        lines.append(f"| {n} | {len(paths)} | {len(bad)} |")
        if bad:
            detail += [f"\n## {n}\n"] + [f"- `{p}`" for p in bad]
    text = "\n".join(lines + detail) + "\n"
    if a.out:
        a.out.write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
