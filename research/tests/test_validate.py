"""Tests for research/validate.py: schema, codebook, PII scan."""
import csv
import shutil
from pathlib import Path

import gen_synthetic as g
import validate as v

ROOT = Path(__file__).resolve().parents[2]


def test_validator_passes_on_committed_data():
    assert v.run() == []


def test_codebook_covers_every_column():
    cb = v.load_codebook()
    data = g.generate(42)
    for name, rows in data.items():
        assert [s["column"] for s in cb[name]] == list(rows[0]), name


def test_survey_question_count_within_limit():
    qids = {s["question_id"] for s in v.load_codebook()["syn_survey_responses"]} - {"system"}
    assert len({q.rstrip("abcdefgh") for q in qids}) <= 22


def _copy_with_edit(tmp_path, fname, col, value, row=0):
    for f in v.SYN_FILES.values():
        shutil.copy(ROOT / "research" / "synthetic" / f, tmp_path / f)
    p = tmp_path / fname
    rows = list(csv.DictReader(p.open()))
    rows[row][col] = value
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader(); w.writerows(rows)
    return v.run(data_dir=tmp_path)


def test_rejects_unknown_venue(tmp_path):
    errs = _copy_with_edit(tmp_path, "syn_interviews.csv", "venue_mentions", "9999-99-999999")
    assert any("venue_mentions" in e for e in errs)


def test_rejects_unflagged_row(tmp_path):
    errs = _copy_with_edit(tmp_path, "syn_survey_responses.csv", "is_synthetic", "0")
    assert any("is_synthetic" in e for e in errs)


def test_rejects_out_of_range_and_bad_genre(tmp_path):
    assert any("nps_concept" in e for e in _copy_with_edit(tmp_path, "syn_survey_responses.csv", "nps_concept", "11"))
    assert any("favorite_genres" in e for e in _copy_with_edit(tmp_path, "syn_interviews.csv", "favorite_genres", "polka"))


def test_rejects_bad_id_prefix_and_quote_prefix(tmp_path):
    assert any("should start" in e for e in _copy_with_edit(tmp_path, "syn_survey_responses.csv", "response_id", "srv-0001"))
    assert any("[SYNTHETIC]" in e for e in _copy_with_edit(tmp_path, "syn_interview_quotes.csv", "text", "hello"))


def test_pii_regexes():
    assert v.EMAIL_RE.search("reach me at someone@example.com")
    assert v.PHONE_RE.search("call (212) 555-0101") and v.PHONE_RE.search("212-555-0101")
    assert not v.PHONE_RE.search("venue 0370-24-138636")
    assert not v.EMAIL_RE.search("https://medium.com/@writer/post")


def test_no_pii_in_research_tree():
    assert v.scan_pii() == []
