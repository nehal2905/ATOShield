"""Train the ATOShield Isolation Forest and calibrate its risk mapping.

Pipeline:
  1. Load ``data/normal.parquet`` (benign events only).
  2. Build the canonical feature matrix via ``features.py`` (single source of truth).
  3. Fit ``StandardScaler`` on the normal features.
  4. Fit ``IsolationForest`` on the SCALED normal data only (fully unsupervised —
     it never sees an attack label).
  5. Calibrate: run ``decision_function`` over the normal set and anchor the
     0..100 risk mapping to percentiles of the resulting anomaly-score
     distribution. Persist anchors to ``calibration.json``.

Artifacts written to ``ml/artifacts/``: model.pkl, scaler.pkl, calibration.json
"""

from __future__ import annotations

import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

import features as F

HERE = os.path.dirname(__file__)
DATA_DIR = os.path.join(HERE, "data")
ART_DIR = os.path.join(HERE, "artifacts")

# Calibration anchors (percentiles of the NORMAL anomaly-score distribution).
# risk 0   <- the 85th percentile of normal behavior: the bulk of normal traffic
#             collapses to a low risk, keeping the false-positive rate sane.
# risk 100 <- the 99.5th percentile of normal anomaly scores; anything more
#             anomalous than virtually all normal traffic saturates at 100.
# Raising LO_PERCENTILE trades a little recall for higher precision; this anchor
# was chosen by inspecting the precision/recall-vs-threshold curve in evaluate.py.
LO_PERCENTILE = 85.0
HI_PERCENTILE = 99.5


RAW_COLUMNS = [
    "login_hour", "ip_change", "device_change", "frequency", "geo_velocity", "failed_attempts",
]


def build_matrix(df: pd.DataFrame) -> np.ndarray:
    rows = df[RAW_COLUMNS].to_dict("records")
    return F.rows_to_matrix(rows)


def main() -> None:
    os.makedirs(ART_DIR, exist_ok=True)
    normal_path = os.path.join(DATA_DIR, "normal.parquet")
    if not os.path.exists(normal_path):
        raise SystemExit(f"Missing {normal_path}. Run generate_dataset.py first.")

    df = pd.read_parquet(normal_path)
    X = build_matrix(df)
    print(f"[train] normal matrix shape: {X.shape}  columns: {F.FEATURE_COLUMNS}")

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(Xs)

    # Calibration: anomaly score = -decision_function over the normal set.
    decision = model.decision_function(Xs)
    anomaly = -decision
    lo = float(np.percentile(anomaly, LO_PERCENTILE))
    hi = float(np.percentile(anomaly, HI_PERCENTILE))
    calibration = {
        "method": "linear_percentile",
        "note": "risk = clamp(100*(-decision_function - lo)/(hi - lo), 0, 100)",
        "lo": lo,
        "hi": hi,
        "lo_percentile": LO_PERCENTILE,
        "hi_percentile": HI_PERCENTILE,
        "normal_anomaly_percentiles": {
            "p1": float(np.percentile(anomaly, 1)),
            "p50": float(np.percentile(anomaly, 50)),
            "p90": float(np.percentile(anomaly, 90)),
            "p99": float(np.percentile(anomaly, 99)),
            "p99_5": float(np.percentile(anomaly, 99.5)),
        },
        "feature_columns": F.FEATURE_COLUMNS,
    }

    joblib.dump(model, os.path.join(ART_DIR, "model.pkl"))
    joblib.dump(scaler, os.path.join(ART_DIR, "scaler.pkl"))
    with open(os.path.join(ART_DIR, "calibration.json"), "w", encoding="utf-8") as fh:
        json.dump(calibration, fh, indent=2)

    # Sanity: distribution of calibrated risk on the normal set.
    risks = np.array([F.apply_calibration(d, calibration) for d in decision])
    print(f"[train] saved model.pkl, scaler.pkl, calibration.json -> {ART_DIR}")
    print(f"[train] calibration anchors: lo={lo:.4f} (p{LO_PERCENTILE}) hi={hi:.4f} (p{HI_PERCENTILE})")
    print(
        f"[train] normal risk distribution: "
        f"mean={risks.mean():.1f} p90={np.percentile(risks,90):.0f} "
        f"p99={np.percentile(risks,99):.0f} %>=60={(risks>=60).mean()*100:.2f}%"
    )


if __name__ == "__main__":
    main()
