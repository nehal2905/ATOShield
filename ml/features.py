"""Canonical feature engineering for ATOShield.

This module is the SINGLE SOURCE OF TRUTH for how a login event is turned into
the numeric vector the Isolation Forest consumes. Both the offline training
pipeline (``ml/train.py``) and the live backend
(``backend/app/core/feature_extractor.py``) MUST use these functions so that the
feature vector seen at training time is byte-for-byte identical to the one seen
at scoring time. A backend test (``test_feature_parity``) enforces this.

Design notes (defensible in a viva):
- Login hour is encoded cyclically with sin/cos so 23:00 and 00:00 are "close"
  in feature space. A raw integer hour would make midnight look maximally far
  from 1am, which is wrong for behavioral modeling.
- Geo-velocity (km/h) is a *continuous engineered feature*, not a binary
  "location changed" flag. A user flying NYC->London is a legitimate location
  change; the discriminator is implied travel *speed*, not the fact of change.
- IP/device change are membership tests against a per-user baseline set
  (0 if known, 1 if new). They are intentionally simple; the richness comes
  from the baseline state, not the encoding.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Dict, List, Sequence

import numpy as np

# ── Canonical column order. DO NOT REORDER without retraining the model. ──
FEATURE_COLUMNS: List[str] = [
    "hour_sin",
    "hour_cos",
    "ip_change",
    "device_change",
    "frequency",
    "geo_velocity",
    "failed_attempts",
]

# Physical / domain constants
GEO_VELOCITY_CAP_KMH: float = 5000.0      # cap implausible/instant jumps
IMPOSSIBLE_TRAVEL_KMH: float = 900.0      # sustained > this == "impossible travel"
EARTH_RADIUS_KM: float = 6371.0


@dataclass(frozen=True)
class RawSignals:
    """Baseline-derived raw signals for a single login event.

    These are produced by the backend (from Redis baseline state) or by the
    dataset generator (synthetically). Encoding into the model vector is done
    here so the two paths cannot drift apart.
    """

    login_hour: float        # 0..23 (can be fractional)
    ip_change: float         # 0.0 known / 1.0 new
    device_change: float     # 0.0 known / 1.0 new
    frequency: float         # logins in trailing 60-min window (>=1, this login counts)
    geo_velocity: float      # implied km/h from previous login
    failed_attempts: float   # failures immediately preceding this success

    def as_dict(self) -> Dict[str, float]:
        return asdict(self)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometers."""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(min(1.0, math.sqrt(a)))
    return EARTH_RADIUS_KM * c


def geo_velocity_kmh(
    prev_lat: float | None,
    prev_lon: float | None,
    cur_lat: float,
    cur_lon: float,
    dt_seconds: float,
) -> float:
    """Implied travel speed (km/h) between previous and current login.

    Returns 0.0 when there is no previous location (cold start) — a first login
    cannot have "impossible travel". The result is capped at GEO_VELOCITY_CAP_KMH
    so a near-zero dt (two logins in the same second from different continents)
    produces a large-but-bounded value instead of infinity.
    """
    if prev_lat is None or prev_lon is None:
        return 0.0
    dist = haversine_km(prev_lat, prev_lon, cur_lat, cur_lon)
    if dist <= 0.0:
        return 0.0
    dt_hours = max(dt_seconds, 1.0) / 3600.0  # floor dt at 1s to avoid div-by-0
    speed = dist / dt_hours
    return float(min(speed, GEO_VELOCITY_CAP_KMH))


def is_impossible_travel(geo_velocity: float) -> bool:
    return geo_velocity > IMPOSSIBLE_TRAVEL_KMH


def encode_row(raw: RawSignals | Dict[str, float]) -> Dict[str, float]:
    """Encode raw signals into the canonical numeric columns (pre-scaling)."""
    if isinstance(raw, RawSignals):
        r = raw.as_dict()
    else:
        r = dict(raw)

    hour = float(r["login_hour"]) % 24.0
    angle = 2.0 * math.pi * hour / 24.0
    return {
        "hour_sin": math.sin(angle),
        "hour_cos": math.cos(angle),
        "ip_change": float(r["ip_change"]),
        "device_change": float(r["device_change"]),
        "frequency": float(r["frequency"]),
        "geo_velocity": float(r["geo_velocity"]),
        "failed_attempts": float(r["failed_attempts"]),
    }


def to_vector(raw: RawSignals | Dict[str, float]) -> np.ndarray:
    """Canonical ordered feature vector (1D, float64) BEFORE scaling."""
    row = encode_row(raw)
    return np.array([row[c] for c in FEATURE_COLUMNS], dtype=np.float64)


def rows_to_matrix(rows: Sequence[RawSignals | Dict[str, float]]) -> np.ndarray:
    """Stack many raw-signal rows into a 2D matrix in canonical column order."""
    return np.vstack([to_vector(r) for r in rows]) if rows else np.empty((0, len(FEATURE_COLUMNS)))


def apply_calibration(decision_value: float, calib: Dict[str, float]) -> int:
    """Map a raw Isolation Forest ``decision_function`` value to a 0..100 risk.

    sklearn convention: ``decision_function`` is HIGHER for inliers and LOWER
    (negative) for outliers. We invert the sign to get an "anomaly score" that
    grows with risk, then linearly map the calibrated [lo, hi] anchor range onto
    [0, 100] and clamp. ``lo``/``hi`` are percentiles of the anomaly score over
    the *normal* training set, computed in ``train.py`` and persisted to
    ``calibration.json`` so training and serving agree exactly.
    """
    anomaly = -float(decision_value)
    lo = float(calib["lo"])
    hi = float(calib["hi"])
    if hi <= lo:
        return 0
    risk = 100.0 * (anomaly - lo) / (hi - lo)
    return int(round(min(100.0, max(0.0, risk))))
