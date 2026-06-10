"""Enforces .cursorrules: backend feature_extractor MUST match ml/features.py.

Because the backend imports the canonical module, parity is true by construction
— this test guarantees nobody silently forks the logic.
"""

import importlib
import os
import sys

import numpy as np
import pytest

from app.core import feature_extractor as fx
from app.core._ml_bridge import features as F

# Independently import the ml module by file path to be a true second source.
ML_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ml"))
sys.path.insert(0, ML_DIR)
ml_features = importlib.import_module("features")


CASES = [
    {"login_hour": 3.5, "ip_change": 1, "device_change": 1, "frequency": 12,
     "geo_velocity": 1500, "failed_attempts": 7},
    {"login_hour": 0, "ip_change": 0, "device_change": 0, "frequency": 1,
     "geo_velocity": 0, "failed_attempts": 0},
    {"login_hour": 23.99, "ip_change": 0, "device_change": 1, "frequency": 3,
     "geo_velocity": 850, "failed_attempts": 2},
]


@pytest.mark.parametrize("raw", CASES)
def test_extractor_matches_ml_features(raw):
    backend_vec = fx.extract_features(raw)
    ml_vec = ml_features.to_vector(raw)
    assert np.allclose(backend_vec, ml_vec), f"feature drift for {raw}"


def test_column_order_matches():
    assert fx.FEATURE_COLUMNS == ml_features.FEATURE_COLUMNS == F.FEATURE_COLUMNS
