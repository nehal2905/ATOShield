"""Per-feature attribution overlay for the dashboard "why was this flagged" radar.

Preferred: ``shap.TreeExplainer`` over the Isolation Forest (the same method as
``ml/explain.py``). If SHAP is unavailable or errors at runtime, we fall back to
a DETERMINISTIC overlay derived from the scaled feature deviations.

IMPORTANT (per .cursorrules): this overlay is EXPLAINABILITY ONLY. It never
produces or alters the risk score — that always comes from the Isolation Forest.
"""

from __future__ import annotations

from typing import Dict

import numpy as np

from app.core._ml_bridge import features as F, try_import_explain

# Features where a larger scaled value is intuitively "more suspicious".
_MONOTONIC_SUSPICIOUS = {"ip_change", "device_change", "frequency", "geo_velocity", "failed_attempts"}


class _ShapAttributor:
    def __init__(self, explain_module, model) -> None:
        self._explain = explain_module
        self._explainer = explain_module.build_explainer(model)

    def attribute(self, scaled_vector: np.ndarray) -> Dict[str, float]:
        return self._explain.attribute(self._explainer, scaled_vector)


class _OverlayAttributor:
    """Deterministic fallback: signed deviation overlay (explainability only)."""

    def attribute(self, scaled_vector: np.ndarray) -> Dict[str, float]:
        v = np.asarray(scaled_vector, dtype=np.float64).reshape(-1)
        out: Dict[str, float] = {}
        for name, val in zip(F.FEATURE_COLUMNS, v):
            if name in _MONOTONIC_SUSPICIOUS:
                out[name] = float(val)            # above-average -> suspicious
            else:  # hour_sin / hour_cos: deviation magnitude matters, not sign
                out[name] = float(abs(val))
        return out


def get_attributor(model):
    """Build the best available attributor once (called lazily by the scorer)."""
    explain_module = try_import_explain()
    if explain_module is not None:
        try:
            attr = _ShapAttributor(explain_module, model)
            # smoke test so we fail over to the overlay if SHAP can't handle it
            attr.attribute(np.zeros(len(F.FEATURE_COLUMNS)))
            return attr
        except Exception:
            pass
    return _OverlayAttributor()
