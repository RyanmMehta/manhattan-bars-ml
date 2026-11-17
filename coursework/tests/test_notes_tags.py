"""Every [N#] tag in an exercise's code has a NOTES.md section, and every section is used in code."""
import re
from pathlib import Path

import pytest

COURSEWORK = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("exercise", ["tiny_transformer", "churn"])
def test_tags_match_notes(exercise):
    folder = COURSEWORK / exercise
    code_tags = set()
    for path in folder.glob("*.py"):
        code_tags |= set(re.findall(r"\[(N\d+)\]", path.read_text()))
    notes = (folder / "NOTES.md").read_text()
    note_tags = set(re.findall(r"^##+ \[(N\d+)\]", notes, flags=re.M))
    # The last section (results / limitations) may have no code tag; everything else must match.
    last = max(note_tags, key=lambda t: int(t[1:]))
    assert code_tags <= note_tags, f"tags in code without a NOTES section: {code_tags - note_tags}"
    assert note_tags - {last} <= code_tags, f"NOTES sections never referenced in code: {note_tags - code_tags - {last}}"
