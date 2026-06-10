import math

import numpy as np
import pytest

import features as F


def test_feature_columns_order_is_stable():
    assert F.FEATURE_COLUMNS == [
        "hour_sin", "hour_cos", "ip_change", "device_change",
        "frequency", "geo_velocity", "failed_attempts",
    ]


def test_cyclic_hour_midnight_close_to_2300():
    v0 = F.to_vector({"login_hour": 0, "ip_change": 0, "device_change": 0,
                      "frequency": 1, "geo_velocity": 0, "failed_attempts": 0})
    v23 = F.to_vector({"login_hour": 23, "ip_change": 0, "device_change": 0,
                       "frequency": 1, "geo_velocity": 0, "failed_attempts": 0})
    v12 = F.to_vector({"login_hour": 12, "ip_change": 0, "device_change": 0,
                       "frequency": 1, "geo_velocity": 0, "failed_attempts": 0})
    # distance in (sin,cos) space: midnight should be much closer to 23:00 than to noon
    d_2300 = np.linalg.norm(v0[:2] - v23[:2])
    d_noon = np.linalg.norm(v0[:2] - v12[:2])
    assert d_2300 < d_noon


def test_haversine_known_distance():
    # NYC -> London ~ 5570 km (allow generous tolerance)
    d = F.haversine_km(40.7128, -74.0060, 51.5074, -0.1278)
    assert 5400 < d < 5700


def test_geo_velocity_cold_start_is_zero():
    assert F.geo_velocity_kmh(None, None, 10, 10, 60) == 0.0


def test_geo_velocity_impossible_travel_flag():
    # ~5570 km in 1 hour -> way over 900 km/h, but capped at 5000
    v = F.geo_velocity_kmh(40.7128, -74.0060, 51.5074, -0.1278, 3600)
    assert v == pytest.approx(5000.0)  # capped
    assert F.is_impossible_travel(v)


def test_geo_velocity_reasonable_drive_not_impossible():
    # 50 km in 1 hour = 50 km/h
    v = F.geo_velocity_kmh(40.0, -74.0, 40.45, -74.0, 3600)
    assert 40 < v < 60
    assert not F.is_impossible_travel(v)


def test_apply_calibration_clamps():
    calib = {"lo": 0.0, "hi": 1.0}
    # decision -0.5 -> anomaly 0.5 -> risk 50
    assert F.apply_calibration(-0.5, calib) == 50
    # very normal (high decision) -> risk 0
    assert F.apply_calibration(5.0, calib) == 0
    # very anomalous (very negative decision) -> risk 100
    assert F.apply_calibration(-50.0, calib) == 100
