"""Process-wide objects built once in create_app()."""

from dataclasses import dataclass, field
from datetime import datetime

from .config import Settings
from .db import Database
from .engine import Engine
from .repo.sources import Sources
from .repo.venues import Catalog
from .timeutil import parse_now


@dataclass
class Ctx:
    settings: Settings
    db: Database
    src: Sources
    engine: Engine
    catalog: Catalog
    genres: tuple[str, ...]
    sim_problems: list[str] = field(default_factory=list)

    def read_now(self, now: str | None) -> datetime:
        return parse_now(now, self.settings.demo_now)

    def write_now(self, now: str | None = None) -> datetime:
        """Writes use server time; in demo mode (DEMO_NOW set) they are stamped at DEMO_NOW so
        they show up in the replayed night. ALLOW_WRITE_NOW=1 lets tests pass `now`."""
        if now and self.settings.allow_write_now:
            return parse_now(now)
        return parse_now(None, self.settings.demo_now)

    @property
    def engine_label(self) -> str:
        return "real" if getattr(self.engine, "name", "stub") == "recs" else "stub"
