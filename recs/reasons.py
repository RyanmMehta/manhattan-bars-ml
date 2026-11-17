"""Reason / missing copy (specs SCORING §5.11, same strings as docs/specs/tools/reference_scoring.py).

Complaint risk never appears here.
"""
from __future__ import annotations

from . import config as C

COMPONENTS = ["genre", "dancing", "crowd", "line", "cover", "distance", "group"]
REASON_MIN_COMPONENT = 0.6  # spec: docs/specs/PARAMETERS.md reason_min_component
GENRE_LABELS = {"hip-hop": "Hip-hop", "r&b": "R&B", "edm": "EDM", "top-40": "Top 40", "soul-funk": "Soul/funk"}
MISSING = {
    "genre": "music unknown",
    "dancing": "no dancing reports",
    "crowd": "no fresh reports — scores are low confidence",
    "line": "line not reported tonight",
    "cover": "cover not reported tonight",
    "distance": "your location unknown",
    "group": "capacity unknown",
}


def genre_label(slug: str) -> str:
    return GENRE_LABELS.get(slug, slug[:1].upper() + slug[1:])


def reasons(comps: dict) -> list[str]:
    """Up to 3: highest weighted score among components with score >= 0.6 and a reason; ties by component order."""
    cands = [(w * s, COMPONENTS.index(k), r) for k, (w, s, r, _) in comps.items() if w > 0 and r and s >= REASON_MIN_COMPONENT]
    return [r for _, _, r in sorted(cands, key=lambda x: (-x[0], x[1]))][: C.MAX_REASONS]


def missing(comps: dict) -> list[str]:
    """One entry per component the prefs care about whose input is unknown (component order)."""
    return [comps[k][3] for k in COMPONENTS if comps[k][0] > 0 and comps[k][3]]
