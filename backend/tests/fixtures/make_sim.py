"""CLI: build the backend test fixture sim DB. `python -m tests.fixtures.make_sim OUT`."""

import sys

from app.config import get_settings
from app.fixture_sim import build_fixture_sim

if __name__ == "__main__":
    s = get_settings()
    out = sys.argv[1] if len(sys.argv) > 1 else s.fixture_sim_db
    print(build_fixture_sim(out, s.launch_venues_csv))
