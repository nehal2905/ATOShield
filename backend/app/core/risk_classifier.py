"""Map a 0..100 risk score to a tier and a recommended response action.

Thresholds come from ``config.py`` (env-tunable), satisfying the "configurable
thresholds" requirement.

| Risk   | Tier     | Action                                   |
|--------|----------|------------------------------------------|
| 0–24   | LOW      | allow                                    |
| 25–49  | MEDIUM   | soft MFA (OTP)                           |
| 50–74  | HIGH     | step-up auth (biometric/hardware key)    |
| 75–100 | CRITICAL | block session + lock + SOC alert         |
"""

from __future__ import annotations

from typing import Tuple

from app.config import settings

ACTIONS = {
    "LOW": "allow",
    "MEDIUM": "soft MFA (OTP)",
    "HIGH": "step-up auth (biometric/hardware key)",
    "CRITICAL": "block session + lock account + SOC alert",
}


def classify(risk: int) -> Tuple[str, str]:
    if risk >= settings.risk_critical_min:
        tier = "CRITICAL"
    elif risk >= settings.risk_high_min:
        tier = "HIGH"
    elif risk >= settings.risk_medium_min:
        tier = "MEDIUM"
    else:
        tier = "LOW"
    return tier, ACTIONS[tier]
