"""SHAP-based per-event explainability for the Isolation Forest.

The dashboard's behavior radar answers "WHY was this login flagged?" by showing
each feature's contribution to the anomaly score. We use ``shap.TreeExplainer``,
which supports the tree ensemble inside an Isolation Forest.

Two entry points:
- ``build_explainer(model)``  -> a cached SHAP explainer (build once at startup).
- ``attribute(explainer, scaled_vector)`` -> dict {feature: contribution}.

The backend imports these so the live attribution is computed with exactly the
same method as offline analysis. If SHAP is unavailable at runtime the backend
falls back to a deterministic overlay (see ``backend/app/core/explainer.py``);
that overlay is explainability ONLY and never replaces the model's score.
"""

from __future__ import annotations

from typing import Dict

import numpy as np

import features as F


def build_explainer(model):
    import shap  # imported lazily so non-explain code paths don't need it
    return shap.TreeExplainer(model)


def attribute(explainer, scaled_vector: np.ndarray) -> Dict[str, float]:
    """Return {feature_name: signed_contribution} for one scaled event vector.

    A more-positive contribution pushes the event toward "anomalous". We flip
    the sign of raw SHAP values because the Isolation Forest's path-length output
    is higher for normal points; flipping makes the radar intuitive (bigger spoke
    == more suspicious).
    """
    v = np.asarray(scaled_vector, dtype=np.float64).reshape(1, -1)
    shap_values = explainer.shap_values(v, check_additivity=False)
    if isinstance(shap_values, list):
        shap_values = shap_values[0]
    contributions = -np.asarray(shap_values).reshape(-1)
    return {name: float(c) for name, c in zip(F.FEATURE_COLUMNS, contributions)}


if __name__ == "__main__":
    import json
    import os
    import joblib
    import pandas as pd

    here = os.path.dirname(__file__)
    art = os.path.join(here, "artifacts")
    model = joblib.load(os.path.join(art, "model.pkl"))
    scaler = joblib.load(os.path.join(art, "scaler.pkl"))
    df = pd.read_parquet(os.path.join(here, "data", "labeled_test.parquet"))
    attack = df[df.is_attack == 1].iloc[0]
    raw = {c: attack[c] for c in F.FEATURE_COLUMNS if c in attack} or {
        "login_hour": attack["login_hour"], "ip_change": attack["ip_change"],
        "device_change": attack["device_change"], "frequency": attack["frequency"],
        "geo_velocity": attack["geo_velocity"], "failed_attempts": attack["failed_attempts"],
    }
    vec = scaler.transform(F.to_vector(raw).reshape(1, -1))
    expl = build_explainer(model)
    print(json.dumps(attribute(expl, vec), indent=2))
