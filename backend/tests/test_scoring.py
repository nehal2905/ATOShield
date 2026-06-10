"""Phase 2 acceptance: end-to-end scoring of a fixture event in < 100 ms."""

import os

import pytest

from app.config import settings
from app.core.scorer import Scorer

ARTIFACTS_PRESENT = all(
    os.path.exists(os.path.join(settings.ml_artifacts_dir, f))
    for f in ("model.pkl", "scaler.pkl", "calibration.json")
)

pytestmark = pytest.mark.skipif(
    not ARTIFACTS_PRESENT,
    reason="ML artifacts missing — run ml/generate_dataset.py && ml/train.py first.",
)


@pytest.fixture(scope="module")
def scorer():
    return Scorer().load()


def test_scores_normal_event_low_risk(scorer):
    res = scorer.score(
        {"login_hour": 14, "ip_change": 0, "device_change": 0,
         "frequency": 1, "geo_velocity": 0, "failed_attempts": 0},
        with_explanation=False,
    )
    assert 0 <= res.risk <= 100
    assert res.tier in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    # a textbook-normal event should not be high risk
    assert res.risk < settings.risk_high_min


def test_scores_obvious_attack_high_risk(scorer):
    res = scorer.score(
        {"login_hour": 3, "ip_change": 1, "device_change": 1,
         "frequency": 30, "geo_velocity": 4000, "failed_attempts": 20},
        with_explanation=False,
    )
    assert res.risk > settings.risk_medium_min


def test_scoring_latency_under_100ms(scorer):
    # warm up (first call JITs numpy paths)
    scorer.score({"login_hour": 9, "ip_change": 0, "device_change": 0,
                  "frequency": 1, "geo_velocity": 0, "failed_attempts": 0},
                 with_explanation=False)
    res = scorer.score({"login_hour": 9, "ip_change": 1, "device_change": 0,
                        "frequency": 2, "geo_velocity": 200, "failed_attempts": 1},
                       with_explanation=False)
    assert res.latency_ms < 100, f"scoring too slow: {res.latency_ms:.1f} ms"


def test_explanation_returns_all_features(scorer):
    res = scorer.score(
        {"login_hour": 2, "ip_change": 1, "device_change": 1,
         "frequency": 15, "geo_velocity": 3000, "failed_attempts": 10},
        with_explanation=True,
    )
    from app.core.feature_extractor import FEATURE_COLUMNS
    assert set(res.contributions.keys()) == set(FEATURE_COLUMNS)
    assert len(res.contributions) == 7
