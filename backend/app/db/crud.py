"""Async database operations (persistence + aggregate stats)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.models import Alert, AuditLog, LoginEvent, RiskScore, User


# ---------------- Users ----------------
async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    res = await db.execute(select(User).where(User.username == username))
    return res.scalar_one_or_none()


async def create_user(db: AsyncSession, username: str, password_hash: str, role: str = "analyst") -> User:
    user = User(username=username, password_hash=password_hash, role=role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ---------------- Events + scores ----------------
async def create_scored_event(
    db: AsyncSession,
    *,
    user_ref: str,
    ip: str,
    device_fp: str,
    geo_lat: float,
    geo_lon: float,
    login_hour: float,
    frequency: float,
    failed_attempts: float,
    raw_features: dict,
    raw_score: float,
    risk: int,
    tier: str,
    contributions: dict,
    timestamp: Optional[datetime] = None,
) -> LoginEvent:
    event = LoginEvent(
        user_ref=user_ref,
        ip=ip,
        device_fp=device_fp,
        geo_lat=geo_lat,
        geo_lon=geo_lon,
        login_hour=login_hour,
        frequency=frequency,
        failed_attempts=failed_attempts,
        raw_features=raw_features,
        timestamp=timestamp or datetime.now(timezone.utc),
    )
    db.add(event)
    await db.flush()  # assign event.id

    score = RiskScore(
        event_id=event.id,
        raw_score=raw_score,
        risk=risk,
        tier=tier,
        contributions=contributions,
    )
    db.add(score)
    await db.commit()
    await db.refresh(event)
    event.score = score
    return event


async def create_alert(db: AsyncSession, *, event_id: int, draft) -> Alert:
    alert = Alert(
        event_id=event_id,
        severity=draft.severity,
        threat_type=draft.threat_type,
        description=draft.description,
        affected_user=draft.affected_user,
        source_ip=draft.source_ip,
        risk=draft.risk,
        status="open",
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


async def list_recent_events(db: AsyncSession, limit: int = 30):
    res = await db.execute(
        select(LoginEvent)
        .options(selectinload(LoginEvent.score))
        .order_by(LoginEvent.timestamp.desc())
        .limit(limit)
    )
    return list(res.scalars().all())


async def list_alerts(db: AsyncSession, status: Optional[str] = None, limit: int = 100):
    stmt = select(Alert).order_by(Alert.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(Alert.status == status)
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def get_alert(db: AsyncSession, alert_id: int) -> Optional[Alert]:
    res = await db.execute(select(Alert).where(Alert.id == alert_id))
    return res.scalar_one_or_none()


async def update_alert_status(db: AsyncSession, alert_id: int, status: str) -> Optional[Alert]:
    alert = await get_alert(db, alert_id)
    if alert is None:
        return None
    alert.status = status
    await db.commit()
    await db.refresh(alert)
    return alert


async def add_audit(db: AsyncSession, *, actor: str, action: str, target: str, detail: dict) -> None:
    db.add(AuditLog(actor=actor, action=action, target=target, detail=detail))
    await db.commit()


# ---------------- Aggregate stats ----------------
async def get_stats(db: AsyncSession) -> dict:
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    events_24h = (await db.execute(
        select(func.count(LoginEvent.id)).where(LoginEvent.timestamp >= since)
    )).scalar_one()

    blocked = (await db.execute(
        select(func.count(RiskScore.id))
        .join(LoginEvent, RiskScore.event_id == LoginEvent.id)
        .where(LoginEvent.timestamp >= since, RiskScore.tier == "CRITICAL")
    )).scalar_one()

    # Anomalies = events scored at/above the alert threshold in the last 24h.
    # Counted directly from risk_scores so it doesn't depend on alert-row state.
    anomalies = (await db.execute(
        select(func.count(RiskScore.id))
        .join(LoginEvent, RiskScore.event_id == LoginEvent.id)
        .where(LoginEvent.timestamp >= since, RiskScore.risk >= settings.alert_threshold)
    )).scalar_one()

    active_sessions = (await db.execute(
        select(func.count(func.distinct(LoginEvent.user_ref))).where(LoginEvent.timestamp >= since)
    )).scalar_one()

    # Hourly histogram (by login_hour bucket) over last 24h
    hour_rows = (await db.execute(
        select(LoginEvent.login_hour).where(LoginEvent.timestamp >= since)
    )).scalars().all()
    hourly = [0] * 24
    for h in hour_rows:
        try:
            hourly[int(h) % 24] += 1
        except (TypeError, ValueError):
            continue

    # Device distribution: new-device vs known-device events (last 24h)
    new_dev = 0
    known_dev = 0
    feat_rows = (await db.execute(
        select(LoginEvent.raw_features).where(LoginEvent.timestamp >= since)
    )).scalars().all()
    for rf in feat_rows:
        if isinstance(rf, dict) and rf.get("device_change", 0):
            new_dev += 1
        else:
            known_dev += 1

    # Tier distribution (last 24h) for the gauge/summary
    tier_rows = (await db.execute(
        select(RiskScore.tier, func.count(RiskScore.id))
        .join(LoginEvent, RiskScore.event_id == LoginEvent.id)
        .where(LoginEvent.timestamp >= since)
        .group_by(RiskScore.tier)
    )).all()
    tier_distribution = {t: c for t, c in tier_rows}

    return {
        "events_24h": int(events_24h or 0),
        "blocked": int(blocked or 0),
        "anomalies": int(anomalies or 0),
        "active_sessions": int(active_sessions or 0),
        "hourly": hourly,
        "device_distribution": {"known": known_dev, "new": new_dev},
        "tier_distribution": tier_distribution,
    }
