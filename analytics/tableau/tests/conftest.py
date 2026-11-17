import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TABLEAU = HERE.parent
ROOT = TABLEAU.parents[1]
sys.path.insert(0, str(TABLEAU))
DB = ROOT / "data" / "manhattan_bars.db"
LAUNCH = ROOT / "data" / "launch_venues.csv"


@pytest.fixture(scope="session")
def exported(tmp_path_factory):
    """Run the exporter (placeholder tonight source) into a tmp dir."""
    if not DB.exists():
        pytest.skip(f"{DB} absent: run the public pipeline first")
    import export_extracts as ex
    out = tmp_path_factory.mktemp("extracts")
    ex.export(DB, out, out / "synthetic", LAUNCH, None, None, placeholder=True)
    return out
