"""Distances (haversine) and walking time."""
from __future__ import annotations

import math

from .config import WALK_KMH

EARTH_R_KM = 6371.0088


def haversine_km(lat1, lon1, lat2, lon2) -> float | None:
    if None in (lat1, lon1, lat2, lon2):
        return None
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R_KM * math.asin(math.sqrt(a))


def walk_minutes(km: float) -> float:
    return km / WALK_KMH * 60.0
