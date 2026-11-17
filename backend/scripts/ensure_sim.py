"""Check live_sim.db (built at build time, v2 §J). Exit 1 if unusable and ALLOW_FIXTURE_SIM=0.

--copy-to-db: Postgres path (v2 §J) — copy sim tables into DATABASE_URL as syn_* tables.
SYNTHETIC: every table handled here is live-sim output, replaced by real twin tables."""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.simdb import EXPECTED, resolve_sim_path  # noqa: E402


def copy_to_db(sim_path: str, url: str) -> None:
    from sqlalchemy import create_engine, text

    eng = create_engine(url)
    src = sqlite3.connect(f"file:{sim_path}?mode=ro", uri=True)
    with eng.begin() as conn:
        for table in EXPECTED:
            have = [r[1] for r in src.execute(f'PRAGMA table_info("{table}")')]
            if not have:
                continue
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            conn.execute(text(f"CREATE TABLE {table} ({', '.join(c + ' TEXT' for c in have)})"))
            rows = src.execute(f"SELECT {', '.join(have)} FROM {table}").fetchall()
            if rows:
                ph = ", ".join(f":{c}" for c in have)
                conn.execute(
                    text(f"INSERT INTO {table} VALUES ({ph})"),
                    [dict(zip(have, r, strict=True)) for r in rows],
                )
            print(f"copied {table}: {len(rows)} rows")
    src.close()


def main() -> int:
    s = get_settings()
    if not s.include_synthetic:
        print("ensure_sim: INCLUDE_SYNTHETIC=0, no sim DB needed")
        return 0
    path, problems = resolve_sim_path(s)
    if path is None:
        print(f"ensure_sim: no usable live_sim.db: {problems}", file=sys.stderr)
        return 1
    print(f"ensure_sim: using {path}" + (f" (fallback: {problems})" if problems else ""))
    if "--copy-to-db" in sys.argv and not s.is_sqlite:
        copy_to_db(path, s.database_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
