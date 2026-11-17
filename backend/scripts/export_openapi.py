"""Write backend/openapi.json (frontend generates TS types from it)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

if __name__ == "__main__":
    app = create_app(Settings(database_url="sqlite:///:memory:", log_level="WARNING"))
    (ROOT / "openapi.json").write_text(json.dumps(app.openapi(), indent=2) + "\n")
    print(ROOT / "openapi.json")
