"""Engine from DATABASE_URL. On SQLite, live_sim.db is ATTACHed read-only as `sim` on every
connection (v2 §D). On Postgres the sim tables are copied in as `syn_*` (v2 §J)."""

import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass

from sqlalchemy import Engine, create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import Settings


@dataclass
class Database:
    engine: Engine
    sessionmaker: sessionmaker
    sim_path: str | None  # SYNTHETIC: attached live_sim.db; None when absent/disabled
    sim_prefix: str  # "sim." on SQLite, "" on Postgres (copied-in syn_ tables)
    sim_available: bool

    def session(self) -> Iterator[Session]:
        s = self.sessionmaker()
        try:
            yield s
        finally:
            s.close()


def _sqlite_path(url: str) -> str:
    path = url.split("sqlite:///", 1)[1] if "sqlite:///" in url else ":memory:"
    return path or ":memory:"


def make_database(settings: Settings, sim_path: str | None) -> Database:
    if settings.is_sqlite:
        path = _sqlite_path(settings.database_url)
        memory = path == ":memory:"

        def creator() -> sqlite3.Connection:
            conn = sqlite3.connect(
                "file::memory:?cache=shared" if memory else f"file:{path}",
                uri=True,
                check_same_thread=False,
            )
            if not memory:
                conn.execute("PRAGMA journal_mode=WAL")
            if sim_path:
                # SYNTHETIC: replace with real tables once pilot data exists (INCLUDE_SYNTHETIC=0)
                conn.execute("ATTACH DATABASE ? AS sim", (f"file:{sim_path}?mode=ro",))
            return conn

        kwargs = {"poolclass": StaticPool} if memory else {}
        engine = create_engine("sqlite://", creator=creator, **kwargs)
        return Database(engine, sessionmaker(engine), sim_path, "sim.", sim_path is not None)

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    has_sim = inspect(engine).has_table("syn_scout_reports")
    return Database(engine, sessionmaker(engine), None, "", has_sim)
