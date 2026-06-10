"""Turn a scored event into an alert (when it crosses the configured threshold).

Threat typing is a small rule layer ON TOP of the model score: the model decides
*whether* something is anomalous; these rules label *what kind* of anomaly it
looks like, which is what an analyst needs to triage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.config import settings


@dataclass
class AlertDraft:
    severity: str
    threat_type: str
    description: str
    affected_user: str
    source_ip: str
    risk: int


def _classify_threat(signals, risk: int) -> tuple[str, str]:
    ip = signals.ip_change >= 1.0
    dev = signals.device_change >= 1.0
    odd_hour = signals.login_hour < 5 or signals.login_hour >= 23

    if signals.impossible_travel:
        return (
            "Impossible Travel",
            f"Implied travel speed {signals.geo_velocity:.0f} km/h exceeds the "
            f"physical threshold ({int(settings.alert_threshold)} risk).",
        )
    if signals.frequency >= 8 and signals.failed_attempts >= 4:
        return (
            "Credential Stuffing",
            f"{int(signals.frequency)} logins/hr with {int(signals.failed_attempts)} "
            "failed attempts — automated guessing pattern.",
        )
    if signals.failed_attempts >= 5:
        return (
            "Brute Force",
            f"{int(signals.failed_attempts)} failed attempts preceding access.",
        )
    if ip and dev and odd_hour:
        return (
            "New Device & IP (Odd Hour)",
            f"First-seen device and IP at {signals.login_hour:.1f}h local — "
            "classic takeover footprint.",
        )
    if ip and dev:
        return ("New Device & IP", "Login from a previously unseen device and network.")
    return ("Behavioral Anomaly", "Isolation Forest flagged a deviation from the user's baseline.")


def build_alert(signals, risk: int, tier: str, user: str, ip: str) -> Optional[AlertDraft]:
    """Return an AlertDraft if risk >= ALERT_THRESHOLD, else None."""
    if risk < settings.alert_threshold:
        return None
    threat_type, description = _classify_threat(signals, risk)
    severity = "critical" if tier == "CRITICAL" else "high" if tier == "HIGH" else "medium"
    return AlertDraft(
        severity=severity,
        threat_type=threat_type,
        description=description,
        affected_user=user,
        source_ip=ip,
        risk=risk,
    )
