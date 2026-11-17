"""Reason / missing templates (specs PRD §5.11). Complaint risk never appears here."""
from __future__ import annotations

from . import config as C

MIN_REASON_SCORE = 0.5


def _pretty_genre(g: str) -> str:
    special = {"r&b": "R&B", "edm": "EDM", "top-40": "Top-40", "hip-hop": "Hip-hop", "soul-funk": "Soul/funk"}
    return special.get(g, g.capitalize())


def _evidence(st: dict) -> str:
    n = st.get("n_reports") or 0
    f = st.get("freshness_minutes")
    parts = []
    if n:
        parts.append(f"{n} report{'s' if n != 1 else ''}")
    if f is not None:
        parts.append(f"{f} min ago")
    return f" ({', '.join(parts)})" if parts else ""


def _text(name: str, ev: dict, st: dict) -> str | None:
    if name == "genre":
        if ev.get("kind") == "live":
            return f"{_pretty_genre(ev['genre'])} playing{_evidence(st)}"
        if ev.get("kind") == "static":
            return f"Usually plays {_pretty_genre(ev['genre']).lower()}"
        return None
    if name == "dancing":
        n = st.get("n_reports") or 0
        if ev.get("want"):
            return f"Dancing reported ({n} report{'s' if n != 1 else ''})"
        return "Low-key, little dancing reported"
    if name == "crowd":
        return f"Crowd ~{ev['crowd']:.1f}/5, close to your {ev['pref']:g}"
    if name == "line":
        if ev["line"] == 0:
            return "No line reported"
        return f"Line ~{ev['line']:.0f} min, under your {ev['max']:g}"
    if name == "cover":
        if ev["cover"] == 0:
            return "No cover tonight"
        return f"Cover ${ev['cover']:.0f}, under your ${ev['max']:g}"
    if name == "distance":
        return "Under 0.1 km away" if ev["km"] < 0.05 else f"{ev['km']:.1f} km away"
    if name == "group":
        return f"Room for a group of {ev['group_size']:g}"
    return None


def reasons(comps: dict, st: dict, prefs: dict) -> list[str]:
    """Up to 3 reasons from the top positive weighted known components."""
    ranked = sorted(
        ((w * s, name) for name, (w, s, known, ev) in comps.items() if known and w > 0 and s >= MIN_REASON_SCORE and ev),
        key=lambda t: (-t[0], t[1]),
    )
    out = []
    for _, name in ranked:
        t = _text(name, comps[name][3], st)
        if t:
            out.append(t)
        if len(out) >= C.MAX_REASONS:
            break
    return out


MISSING_TEXT = {
    "genre": "music unknown",
    "dancing": "no dancing reports",
    "crowd": "no fresh reports — scores are low confidence",
    "line": "line not reported tonight",
    "cover": "cover not reported tonight",
    "distance": "your location is unknown",
    "group": "capacity unknown",
}


def missing(comps: dict, st: dict, prefs: dict) -> list[str]:
    """One entry per null field the prefs care about (weight > 0 and unknown)."""
    out = []
    order = ["crowd", "genre", "dancing", "line", "cover", "distance", "group"]
    for name in order:
        w, s, known, _ = comps[name]
        if w > 0 and not known:
            out.append(MISSING_TEXT[name])
    return out
