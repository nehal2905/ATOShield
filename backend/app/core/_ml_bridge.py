"""Bridge that imports the CANONICAL ml/features.py into the backend.

The backend deliberately reuses the exact same ``features`` module that trained
the model, rather than re-implementing the transform. This makes feature parity
true by construction; ``backend/tests/test_feature_parity.py`` still asserts it
so any accidental divergence (e.g. someone copy-pasting a fork) is caught.
"""

from __future__ import annotations

import importlib
import os
import sys

from app.config import settings


def _locate_ml_dir() -> str:
    candidates = [
        settings.ml_dir,
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml")),
        "/app/ml",
    ]
    for c in candidates:
        if c and os.path.exists(os.path.join(c, "features.py")):
            return c
    # Fall back to the first candidate; import will raise a clear error.
    return candidates[0]


_ML_DIR = _locate_ml_dir()
if _ML_DIR not in sys.path:
    sys.path.insert(0, _ML_DIR)

features = importlib.import_module("features")


def try_import_explain():
    """Return the ml.explain module, or None if SHAP isn't importable."""
    try:
        return importlib.import_module("explain")
    except Exception:
        return None
