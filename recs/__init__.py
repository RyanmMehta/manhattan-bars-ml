"""recs — live venue state, scoring, crowd model, clustering, routing for Nightlife Autopilot.

Public interface (CONTRACTS.md "Python interface"):
    live_state.compute / compute_all, scoring.recommend, routing.plan_night
"""
from . import live_state, scoring, routing  # noqa: F401

__all__ = ["live_state", "scoring", "routing"]
__version__ = "0.1.0"
