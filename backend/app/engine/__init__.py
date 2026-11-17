import importlib
import logging

from .base import Engine
from .stub import StubEngine

log = logging.getLogger("engine")


def get_engine(mode: str = "auto") -> Engine:
    """auto: real recs if importable else stub; recs: require recs; stub: always stub."""
    if mode == "stub":
        return StubEngine()
    try:
        recs = importlib.import_module("recs")
        from .recs_engine import RecsEngine

        return RecsEngine(recs)
    except ImportError as exc:
        if mode == "recs":
            raise
        log.info("recs not importable (%s); using stub engine", exc)
        return StubEngine()


__all__ = ["Engine", "StubEngine", "get_engine"]
