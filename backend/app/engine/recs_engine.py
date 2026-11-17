"""Adapter over the real `recs` package (ml-recs). Import only through get_engine()."""

import logging
from datetime import datetime
from typing import Any

from ..timeutil import NY
from .stub import StubEngine

log = logging.getLogger("engine")


class RecsEngine:
    """Calls recs; any exception falls back to the stub for that call (RULES §4)."""

    name = "recs"

    def __init__(self, recs_module: Any) -> None:
        from recs import live_state, routing, scoring  # noqa: F401  (import check)

        self.live_state, self.scoring, self.routing = live_state, scoring, routing
        self.stub = StubEngine()
        self.last_served = "recs"

    def _call(self, fn_name: str, real: Any, *args: Any) -> Any:
        try:
            out = real(*args)
            self.last_served = "recs"
            return out
        except Exception as exc:  # recs drift must never 500 the API
            log.warning("recs.%s failed, using stub: %r", fn_name, exc)
            self.last_served = "stub"
            return getattr(self.stub, fn_name)(*args)

    def cluster_info(self, venue_id: str) -> tuple[str | None, str | None]:
        """Short label + raw description from recs' committed clustering artifacts (optional)."""
        try:
            from recs import clustering

            return clustering.label_for(venue_id), clustering.description_for(venue_id)
        except Exception:  # artifacts or module missing: fields stay null
            return None, None

    @staticmethod
    def _ny(now: datetime) -> datetime:
        return now.astimezone(NY)

    def compute(self, venue_id: str, reports: Any, updates: Any, now: datetime) -> dict:
        return self._call(
            "compute", self.live_state.compute, venue_id, reports, updates, self._ny(now)
        )

    def compute_all(self, reports_df: Any, updates_df: Any, now: datetime) -> list[dict]:
        return self._call(
            "compute_all", self.live_state.compute_all, reports_df, updates_df, self._ny(now)
        )

    def recommend(self, prefs: dict, states: Any, venues: Any, now: datetime) -> list[dict]:
        return self._call("recommend", self.scoring.recommend, prefs, states, venues, self._ny(now))

    def plan_night(
        self, prefs: dict, states: Any, venues: Any, start_time: datetime, n_stops: int = 3
    ) -> list[dict]:
        return self._call(
            "plan_night",
            self.routing.plan_night,
            prefs,
            states,
            venues,
            self._ny(start_time),
            n_stops,
        )
