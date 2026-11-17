"""Shared genre vocabulary (v2 §E). Source of truth: simulator/config/genres.json (live-sim)."""

import json
from functools import lru_cache
from pathlib import Path

VENDORED_GENRES = [
    "hip-hop",
    "r&b",
    "afrobeats",
    "latin",
    "reggaeton",
    "house",
    "techno",
    "edm",
    "disco",
    "pop",
    "top-40",
    "throwbacks",
    "indie",
    "rock",
    "punk",
    "jazz",
    "soul-funk",
]


@lru_cache
def load_genres(path: str) -> tuple[str, ...]:
    p = Path(path)
    if p.exists():
        data = json.loads(p.read_text())
        if isinstance(data, dict):
            data = data.get("genres") or data.get("slugs") or list(data)
        slugs = [g["slug"] if isinstance(g, dict) else g for g in data]
        if slugs:
            return tuple(slugs)
    return tuple(VENDORED_GENRES)
