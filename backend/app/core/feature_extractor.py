"""Raw signals -> model feature vector.

By design this module DELEGATES the encoding to the canonical ``ml/features.py``
(imported via the ML bridge). Reusing the exact training-time transform makes
feature parity true by construction; ``tests/test_feature_parity.py`` asserts it
to catch any accidental divergence.
"""

from __future__ import annotations

from typing import Dict, Mapping

import numpy as np

from app.core._ml_bridge import features as F

FEATURE_COLUMNS = F.FEATURE_COLUMNS


def extract_features(raw_signals: Mapping[str, float]) -> np.ndarray:
    """Return the canonical ordered feature vector (pre-scaling) for one event."""
    return F.to_vector(raw_signals)


def feature_dict(raw_signals: Mapping[str, float]) -> Dict[str, float]:
    """Return the named (encoded) feature columns for storage/debugging."""
    return F.encode_row(raw_signals)
