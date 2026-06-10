"""Orchestrates the full scoring pipeline for ingested and simulated events.

Ingest path (``/api/events``):
  baseline.compute_and_update -> scorer.score -> alert_engine -> persist ->
  broadcast(event[, alert], stats)

Simulate path (``/api/simulate``):
  scorer.score(raw sliders) -> assemble a human-readable pipeline trace.
  No baseline mutation, no persistence.
"""

#from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import baseline
from app.core import alert_engine
from app.core.scorer import get_scorer
from app.db import crud
from app.schemas.events import (
    LoginEventIn,
    PipelineStep,
    ScoredEventOut,
    SimulateIn,
    SimulateOut,
)
from app.ws.manager import manager


async def process_login_event(db: AsyncSession, payload: LoginEventIn) -> ScoredEventOut:
    ts_dt = payload.timestamp or datetime.now(timezone.utc)
    ts_epoch = ts_dt.timestamp()

    # 1) read prior baseline, compute signals, then update baseline
    signals = await baseline.compute_and_update(
        user=payload.user,
        ip=payload.ip,
        device_fp=payload.device_fp,
        geo_lat=payload.geo_lat,
        geo_lon=payload.geo_lon,
        ts=ts_epoch,
        success=payload.success,
        failed_attempts=payload.failed_attempts,
    )

    # 2) score (model decides anomaly; explainer overlays the "why")
    result = get_scorer().score(signals.to_raw(), with_explanation=True)

    # 3) alert?
    draft = alert_engine.build_alert(signals, result.risk, result.tier, payload.user, payload.ip)

    # 4) persist
    event = await crud.create_scored_event(
        db,
        user_ref=payload.user,
        ip=payload.ip,
        device_fp=payload.device_fp,
        geo_lat=payload.geo_lat,
        geo_lon=payload.geo_lon,
        login_hour=signals.login_hour,
        frequency=signals.frequency,
        failed_attempts=signals.failed_attempts,
        raw_features=signals.to_raw(),
        raw_score=result.raw_score,
        risk=result.risk,
        tier=result.tier,
        contributions=result.contributions,
        timestamp=ts_dt,
    )

    alert_id = None
    threat_type = None
    if draft is not None:
        alert = await crud.create_alert(db, event_id=event.id, draft=draft)
        alert_id = alert.id
        threat_type = draft.threat_type

    out = ScoredEventOut(
        id=event.id,
        user=payload.user,
        ip=payload.ip,
        device_fp=payload.device_fp,
        geo_lat=payload.geo_lat,
        geo_lon=payload.geo_lon,
        timestamp=ts_dt,
        login_hour=signals.login_hour,
        frequency=signals.frequency,
        failed_attempts=signals.failed_attempts,
        ip_change=signals.ip_change,
        device_change=signals.device_change,
        geo_velocity=signals.geo_velocity,
        impossible_travel=signals.impossible_travel,
        raw_score=result.raw_score,
        risk=result.risk,
        tier=result.tier,
        action=result.action,
        contributions=result.contributions,
        alert_id=alert_id,
        threat_type=threat_type,
    )

    # 5) broadcast
    await manager.publish({"type": "event", "payload": out.model_dump(mode="json")})
    if alert_id is not None:
        await manager.publish({
            "type": "alert",
            "payload": {
                "id": alert_id,
                "event_id": event.id,
                "severity": draft.severity,
                "threat_type": draft.threat_type,
                "description": draft.description,
                "affected_user": draft.affected_user,
                "source_ip": draft.source_ip,
                "risk": draft.risk,
                "status": "open",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        })
    stats = await crud.get_stats(db)
    await manager.publish({"type": "stats", "payload": stats})

    return out


async def process_simulation(payload: SimulateIn) -> SimulateOut:
    raw = payload.model_dump()
    trace: list[PipelineStep] = [
        PipelineStep(step="input", detail="Received raw feature vector from controls", data=raw),
    ]

    scorer = get_scorer()
    result = scorer.score(raw, with_explanation=True)

    trace.append(PipelineStep(
        step="encode",
        detail="Cyclic-encoded hour + assembled canonical feature vector",
        data=result.features,
    ))
    trace.append(PipelineStep(
        step="scale",
        detail="StandardScaler applied (training-time mean/variance)",
    ))
    trace.append(PipelineStep(
        step="model",
        detail="IsolationForest.decision_function (negative = anomalous)",
        data={"raw_score": round(result.raw_score, 5)},
    ))
    trace.append(PipelineStep(
        step="calibrate",
        detail="Percentile calibration -> 0..100 risk",
        data={"risk": result.risk},
    ))
    trace.append(PipelineStep(
        step="classify",
        detail=f"Risk {result.risk} -> {result.tier}",
        data={"tier": result.tier, "action": result.action},
    ))
    trace.append(PipelineStep(
        step="explain",
        detail="Per-feature attribution (radar overlay)",
        data=result.contributions,
    ))

    impossible = bool(raw["geo_velocity"] > baseline.F.IMPOSSIBLE_TRAVEL_KMH)
    out = ScoredEventOut(
        id=None,
        user="(simulation)",
        ip="0.0.0.0",
        device_fp="(sim)",
        geo_lat=0.0,
        geo_lon=0.0,
        timestamp=datetime.now(timezone.utc),
        login_hour=raw["login_hour"],
        frequency=raw["frequency"],
        failed_attempts=raw["failed_attempts"],
        ip_change=raw["ip_change"],
        device_change=raw["device_change"],
        geo_velocity=raw["geo_velocity"],
        impossible_travel=impossible,
        raw_score=result.raw_score,
        risk=result.risk,
        tier=result.tier,
        action=result.action,
        contributions=result.contributions,
    )
    return SimulateOut(result=out, trace=trace)
