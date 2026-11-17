"""List nightlife/* workstream branches, their head, and whether they've signalled done
(docs/workstreams/<name>.md exists on the branch) and whether integration already contains them.

Usage: git fetch origin && python -I scripts/integration/merge_status.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORDER = ["specs", "research", "tableau", "coursework", "live-sim", "ml-recs", "backend", "frontend"]


def git(*a, check=True):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, check=check)


def main() -> int:
    print(f"{'branch':12} {'head':9} {'done':5} {'merged':7} last commit")
    for n in ORDER:
        ref = f"origin/nightlife/{n}"
        head = git("rev-parse", "--short", ref, check=False).stdout.strip() or "-"
        done = git("cat-file", "-e", f"{ref}:docs/workstreams/{n}.md", check=False).returncode == 0
        merged = git("merge-base", "--is-ancestor", ref, "HEAD", check=False).returncode == 0
        last = git("log", "-1", "--format=%ci %s", ref, check=False).stdout.strip()[:80]
        print(f"{n:12} {head:9} {'yes' if done else 'no':5} {'yes' if merged else 'no':7} {last}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
