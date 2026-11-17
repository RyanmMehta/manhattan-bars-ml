"""Lint docs/specs (stdlib only).  python -I docs/specs/tools/check_docs.py

Checks: every doc has a Purpose/Status/Last updated header; every parameter-like name in the
specs exists in PARAMETERS.md's JSON block and every JSON key has a table row; US- ids are
defined once; intra-repo Markdown links resolve; Mermaid blocks use known diagram types; golden
files carry is_synthetic: 1; every synthetic file is listed in docs/synthetic/specs.md.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_scoring as R  # noqa: E402

SPECS = Path(__file__).resolve().parent.parent
REPO = SPECS.parent.parent
REGISTRY = REPO / "docs" / "synthetic" / "specs.md"
MERMAID_TYPES = ("flowchart", "graph", "sequenceDiagram", "stateDiagram-v2", "stateDiagram",
                 "classDiagram", "erDiagram", "gantt", "pie")
PARAM_RE = re.compile(r"`((?:H|match_w|vibe_w|rep|pts|bounty|trend|display|level|w|conf|agree|"
                      r"stale|default|outlier|rate|consensus|points|dispute|operator|genre|"
                      r"min|max|unknown|static|group|rank|reason|line|walk|dwell|cutoff|future|"
                      r"presence|velocity|new|diverse|earth)_[a-z_]+)`")
NOT_PARAMS = {"line_minutes", "max_cover_usd", "max_line_minutes", "max_distance_km",
              "group_size", "min_age", "rank_score", "w_rep", "w_ver", "w_status", "w_src",
              "w_time", "max_total_walk_minutes", "dwell_minutes", "reason_min", "agree",
              "new_scout", "genre_label", "presence_radius", "w_i", "rep_lr_", "points_ledger",
              "rate_limited", "owner_own_venue", "match_score", "rank_conf", "trend_delta_",
              "default_", "line_n", "display_name", "group_size_", "level_", "min_field"}


def docs() -> list[Path]:
    """Markdown files owned by specs."""
    return sorted(SPECS.rglob("*.md")) + [REPO / "docs" / "workstreams" / "specs.md", REGISTRY]


def header_errors() -> list[str]:
    """Each doc must have Purpose/Status/Last updated in its first 8 lines."""
    errs = []
    for p in docs():
        head = "\n".join(p.read_text(encoding="utf-8").splitlines()[:8]) if p.exists() else ""
        for key in ("Purpose:", "Status:", "Last updated:"):
            if key not in head:
                errs.append(f"{p.relative_to(REPO)}: header lacks '{key}'")
    return errs


def param_errors() -> list[str]:
    """Parameter names used in docs exist; every JSON key has a table row."""
    errs = []
    keys = set(R.P)
    table = (SPECS / "PARAMETERS.md").read_text(encoding="utf-8").split("## Machine-readable block")[0]
    for k in sorted(keys):
        if f"`{k}`" not in table:
            errs.append(f"PARAMETERS.md: JSON key {k} has no table row")
    for p in docs():
        if not p.exists():
            continue
        for name in PARAM_RE.findall(p.read_text(encoding="utf-8")):
            if name not in keys and name not in NOT_PARAMS:
                errs.append(f"{p.relative_to(REPO)}: `{name}` is not in PARAMETERS.md")
    return errs


def story_errors() -> list[str]:
    """US ids are defined once (bold definition) in requirements.md."""
    text = (SPECS / "requirements.md").read_text(encoding="utf-8")
    ids = re.findall(r"^\*\*(US-[A-Z]+-\d+)", text, re.M)
    dups = sorted({i for i in ids if ids.count(i) > 1})
    return [f"requirements.md: duplicate {i}" for i in dups] + (
        ["requirements.md: no US ids"] if not ids else [])


def link_errors() -> list[str]:
    """Relative Markdown links resolve to files or folders."""
    errs = []
    for p in docs():
        if not p.exists():
            continue
        for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", p.read_text(encoding="utf-8")):
            if re.match(r"[a-z]+:", target):
                continue
            if not (p.parent / target).exists():
                errs.append(f"{p.relative_to(REPO)}: broken link {target}")
    return errs


def mermaid_errors() -> list[str]:
    """Every ```mermaid block starts with a known diagram type."""
    errs = []
    for p in docs():
        if not p.exists():
            continue
        for block in re.findall(r"```mermaid\n(.*?)```", p.read_text(encoding="utf-8"), re.S):
            first = block.strip().split()[0] if block.strip() else ""
            if first not in MERMAID_TYPES:
                errs.append(f"{p.relative_to(REPO)}: unknown mermaid type '{first}'")
    return errs


def synthetic_errors() -> list[str]:
    """Golden files are marked synthetic and listed in the registry."""
    errs = []
    registry = REGISTRY.read_text(encoding="utf-8") if REGISTRY.exists() else ""
    files = sorted((SPECS / "golden_synthetic").glob("*.json")) + [SPECS / "golden_vectors.json"]
    for f in files:
        # SYNTHETIC: golden fixtures (test data, not replaced)
        if json.loads(f.read_text(encoding="utf-8")).get("is_synthetic") != 1:
            errs.append(f"{f.name}: lacks is_synthetic: 1")
        if f.name not in registry:
            errs.append(f"{f.name}: not listed in docs/synthetic/specs.md")
    return errs


def main() -> int:
    """Run all checks."""
    errs = (header_errors() + param_errors() + story_errors() + link_errors()
            + mermaid_errors() + synthetic_errors())
    for e in errs:
        print("FAIL", e)
    print(f"check_docs: {len(docs())} docs, {len(errs)} errors -> {'FAIL' if errs else 'PASS'}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
