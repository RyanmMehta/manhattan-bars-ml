"""Tests for the SYNTHETIC research generator (research/gen_synthetic.py)."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

import gen_synthetic as g

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_GENRES = ["hip-hop", "r&b", "afrobeats", "latin", "reggaeton", "house", "techno", "edm",
                   "disco", "pop", "top-40", "throwbacks", "indie", "rock", "punk", "jazz", "soul-funk"]


def _run(out: Path, seed: int = 42) -> dict[str, str]:
    subprocess.run([sys.executable, "-I", str(ROOT / "research" / "gen_synthetic.py"),
                    "--seed", str(seed), "--out-dir", str(out)], check=True, capture_output=True)
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob("*.csv"))}


def test_determinism_same_seed(tmp_path):
    a, b = _run(tmp_path / "a"), _run(tmp_path / "b")
    assert len(a) == 3 and a == b


def test_different_seed_differs(tmp_path):
    assert _run(tmp_path / "a", 42) != _run(tmp_path / "b", 43)


def test_committed_csvs_match_seed_42(tmp_path):
    fresh = _run(tmp_path)
    committed = {n: hashlib.sha256((ROOT / "research" / "synthetic" / n).read_bytes()).hexdigest() for n in fresh}
    assert fresh == committed, "re-run: python -I research/gen_synthetic.py --seed 42"


def test_no_db_written(tmp_path):
    def hashes():
        return {p.name: (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
                for p in (ROOT / "data").glob("*.db")}
    before = hashes()
    _run(tmp_path)
    assert hashes() == before
    assert not list(tmp_path.glob("*.db"))


def test_counts_flags_and_ids():
    data = g.generate(42, 15, 300)
    assert len(data["syn_interviews"]) == 15 and len(data["syn_survey_responses"]) == 300
    segs = [r["segment"] for r in data["syn_interviews"]]
    assert (segs.count("consumer"), segs.count("scout"), segs.count("operator")) == (8, 3, 4)
    for name, rows in data.items():
        assert all(r["is_synthetic"] == 1 for r in rows), name
        assert all(str(next(iter(r.values()))).startswith("syn-") for r in rows), name
    assert all(q["text"].startswith("[SYNTHETIC] ") for q in data["syn_interview_quotes"])


def test_genre_constant_matches_contract():
    assert g.GENRES_FALLBACK == CONTRACT_GENRES


def test_genre_constant_matches_simulator_json():
    path = ROOT / "simulator" / "config" / "genres.json"
    if not path.exists():
        pytest.skip("simulator/config/genres.json not on this branch yet")
    assert sorted(g.load_genres()) == sorted(CONTRACT_GENRES)


def test_genres_and_venues_in_vocab():
    data = g.generate(42)
    venues = set(g.load_launch_venue_ids())
    for r in data["syn_interviews"]:
        assert set(r["favorite_genres"].split("|")) <= set(CONTRACT_GENRES)
        assert set(r["venue_mentions"].split("|")) <= venues
    for r in data["syn_survey_responses"]:
        if r["favorite_genres"]:
            assert set(r["favorite_genres"].split("|")) <= set(CONTRACT_GENRES)


def test_every_prior_is_marked_synthetic():
    src = (ROOT / "research" / "gen_synthetic.py").read_text()
    block = src.split("PRIORS = {", 1)[1].split("\n}\n", 1)[0]
    keys = [ln for ln in block.splitlines() if ln.startswith('    "')]
    comments = [ln for ln in block.splitlines() if "# SYNTHETIC:" in ln]
    assert keys and len(comments) >= len([k for k in keys if k.strip().endswith(("[", "{"))]) // 2
    assert len(comments) >= 15


def test_summary_tables_synthetic_flag_and_columns():
    import analysis
    rows = analysis.build("synthetic")
    assert rows and all(r["is_synthetic"] == 1 for r in rows)
    assert list(rows[0]) == ["metric", "segment", "value", "n", "is_synthetic"]
    assert rows == analysis.build("synthetic")
