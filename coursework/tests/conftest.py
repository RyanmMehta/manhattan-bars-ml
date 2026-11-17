"""Shared pytest setup: make `import coursework...` work and expose the fixture folder."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "synthetic"  # SYNTHETIC: hand-made test data
