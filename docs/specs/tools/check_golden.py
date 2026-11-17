"""Check golden vectors against the reference oracle (stdlib only).

    python -I docs/specs/tools/check_golden.py          # verify
    python -I docs/specs/tools/check_golden.py --regen  # rebuild expected blocks, then verify

Checks: every golden_synthetic/G*.json equals a fresh build (exact for states and
recommendations; debug floats within 1e-9); golden_vectors.json bundles the same vectors;
every file is marked is_synthetic; contract anchors G1 (vibe 65, conf 0.67) and G5
(match 83) hold; no rounded output sits within 1e-6 of a .5 rounding tie.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_golden as B  # noqa: E402


def close(a: object, b: object, tol: float = 1e-9) -> bool:
    """Deep equality with float tolerance."""
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(close(a[k], b[k], tol) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(close(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return math.isclose(a, b, abs_tol=tol)
    return a == b


def near_tie(x: float | None, ndigits: int) -> bool:
    """True if x is within 1e-6 of a half-step at ndigits (fragile rounding)."""
    if x is None:
        return False
    frac = (abs(x) * 10 ** ndigits) % 1
    return abs(frac - 0.5) < 1e-6


def tie_errors(vec: dict) -> list[str]:
    """Report raw values that sit on a rounding tie."""
    errs = []
    for vid, d in vec["expected"]["debug"].items():
        for key, nd in (("vibe_raw", 0), ("conf_raw", 2), ("crowd_raw", 1),
                        ("dancing_raw", 1), ("match_raw", 0)):
            if near_tie(d.get(key), nd):
                errs.append(f"{vec['id']} {vid} {key}={d[key]} is a rounding tie")
    return errs


def anchor_errors(vectors: dict) -> list[str]:
    """Contract v2 §A anchors."""
    errs = []
    g1 = vectors["G1"]["expected"]["states"][0]
    if (g1["vibe_score"], g1["confidence"]) != (65, 0.67):
        errs.append(f"G1 anchor broken: vibe {g1['vibe_score']} conf {g1['confidence']}")
    g5 = vectors["G5"]["expected"]["recommendations"][0]
    if g5["match_score"] != 83:
        errs.append(f"G5 anchor broken: match {g5['match_score']}")
    return errs


def check() -> list[str]:
    """Return a list of error strings (empty = pass)."""
    errs = []
    fresh = {v["id"]: v for v in B.build_all()}
    for vid, vec in fresh.items():
        path = B.OUT_DIR / f"{vec['name']}.json"
        if not path.exists():
            errs.append(f"missing {path}")
            continue
        # SYNTHETIC: golden fixture (test data; never replaced by real data)
        stored = json.loads(path.read_text(encoding="utf-8"))
        if stored.get("is_synthetic") != 1:
            errs.append(f"{path.name} lacks is_synthetic: 1")
        for key in ("states", "recommendations", "ui"):
            if stored["expected"][key] != vec["expected"][key]:
                errs.append(f"{vid} expected.{key} differs from oracle")
        if not close(stored["expected"]["debug"], vec["expected"]["debug"]):
            errs.append(f"{vid} expected.debug differs from oracle")
        if not close({k: v for k, v in stored.items() if k != "expected"},
                     {k: v for k, v in vec.items() if k != "expected"}):
            errs.append(f"{vid} inputs differ from build_golden.py")
        errs += tie_errors(vec)
    bundle = json.loads(B.BUNDLE.read_text(encoding="utf-8"))
    if bundle.get("is_synthetic") != 1 or not close(bundle, B.bundle(list(fresh.values()))):
        errs.append("golden_vectors.json is out of date (run --regen)")
    return errs + anchor_errors(fresh)


def main() -> int:
    """CLI entry point."""
    if "--regen" in sys.argv:
        B.write_all()
    errs = check()
    for e in errs:
        print("FAIL", e)
    n = len(B.vector_inputs())
    print(f"check_golden: {n} vectors, {len(errs)} errors -> {'FAIL' if errs else 'PASS'}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
