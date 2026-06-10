"""The scoring path. Loads model artifacts ONCE at startup and scores in <100ms.

    extract_features(raw) -> vector
    scaler.transform(vector)
    raw = model.decision_function(scaled)   # sklearn: negative == anomalous
    risk = calibrate(raw)                    # -> 0..100  (ml.features.apply_calibration)
    tier, action = risk_classifier.classify(risk)
    contributions = explainer.attribute(scaled)

The model/scaler/calibration are NEVER reloaded per request.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Dict, Mapping, Optional

import joblib
import numpy as np

from app.config import settings
from app.core import feature_extractor as fx
from app.core import risk_classifier as rc
from app.core._ml_bridge import features as F


@dataclass
class ScoreResult:
    raw_score: float
    risk: int
    tier: str
    action: str
    contributions: Dict[str, float] = field(default_factory=dict)
    features: Dict[str, float] = field(default_factory=dict)
    latency_ms: float = 0.0


class Scorer:
    def __init__(self, artifacts_dir: Optional[str] = None) -> None:
        self.dir = artifacts_dir or settings.ml_artifacts_dir
        self.model = None
        self.scaler = None
        self.calibration: Dict[str, float] = {}
        self._explainer = None  # lazy SHAP

    def load(self) -> "Scorer":
        model_path = os.path.join(self.dir, "model.pkl")
        scaler_path = os.path.join(self.dir, "scaler.pkl")
        calib_path = os.path.join(self.dir, "calibration.json")
        missing = [p for p in (model_path, scaler_path, calib_path) if not os.path.exists(p)]
        if missing:
            raise FileNotFoundError(
                f"ML artifacts missing: {missing}. Run ml/train.py and mount ml/artifacts."
            )
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        with open(calib_path, encoding="utf-8") as fh:
            self.calibration = json.load(fh)
        return self

    @property
    def ready(self) -> bool:
        return self.model is not None and self.scaler is not None

    def _get_explainer(self):
        if self._explainer is None:
            from app.core.explainer import get_attributor
            self._explainer = get_attributor(self.model)
        return self._explainer

    def score(self, raw_signals: Mapping[str, float], with_explanation: bool = True) -> ScoreResult:
        if not self.ready:
            raise RuntimeError("Scorer not loaded. Call load() at startup.")
        t0 = time.perf_counter()

        vector = fx.extract_features(raw_signals).reshape(1, -1)
        scaled = self.scaler.transform(vector)
        raw_score = float(self.model.decision_function(scaled)[0])
        risk = F.apply_calibration(raw_score, self.calibration)
        tier, action = rc.classify(risk)

        contributions: Dict[str, float] = {}
        if with_explanation:
            contributions = self._get_explainer().attribute(scaled[0])

        return ScoreResult(
            raw_score=raw_score,
            risk=risk,
            tier=tier,
            action=action,
            contributions=contributions,
            features=fx.feature_dict(raw_signals),
            latency_ms=(time.perf_counter() - t0) * 1000.0,
        )


_scorer: Optional[Scorer] = None


def get_scorer() -> Scorer:
    global _scorer
    if _scorer is None:
        _scorer = Scorer().load()
    return _scorer


def set_scorer(scorer: Scorer) -> None:
    """Inject a pre-built scorer (used by app startup / tests)."""
    global _scorer
    _scorer = scorer
