"""Geo-velocity / impossible-travel helpers.

Thin wrappers over the canonical implementation in ``ml/features.py`` so there
is exactly one haversine in the codebase.
"""

from __future__ import annotations

from app.core._ml_bridge import features as F

haversine_km = F.haversine_km
geo_velocity_kmh = F.geo_velocity_kmh
is_impossible_travel = F.is_impossible_travel
IMPOSSIBLE_TRAVEL_KMH = F.IMPOSSIBLE_TRAVEL_KMH
GEO_VELOCITY_CAP_KMH = F.GEO_VELOCITY_CAP_KMH
