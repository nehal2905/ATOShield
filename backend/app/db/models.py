"""SQLAlchemy 2.0 ORM models for ATOShield.

JSON columns use JSONB on PostgreSQL and fall back to generic JSON on SQLite
(used in CI/tests), via ``with_variant``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

JSONType = JSON().with_variant(JSONB(), "postgresql")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="analyst")  # 'analyst' | 'admin'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class LoginEvent(Base):
    __tablename__ = "login_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_ref: Mapped[str] = mapped_column(String(128), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    ip: Mapped[str] = mapped_column(String(64))
    device_fp: Mapped[str] = mapped_column(String(128))
    geo_lat: Mapped[float] = mapped_column(Float)
    geo_lon: Mapped[float] = mapped_column(Float)
    login_hour: Mapped[float] = mapped_column(Float)
    frequency: Mapped[float] = mapped_column(Float)
    failed_attempts: Mapped[float] = mapped_column(Float)
    raw_features: Mapped[dict] = mapped_column(JSONType, default=dict)

    score: Mapped["RiskScore"] = relationship(back_populates="event", uselist=False)

    __table_args__ = (Index("ix_login_events_ts", "timestamp"),)


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("login_events.id", ondelete="CASCADE"), index=True)
    raw_score: Mapped[float] = mapped_column(Float)
    risk: Mapped[int] = mapped_column(Integer)
    tier: Mapped[str] = mapped_column(String(16))
    contributions: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    event: Mapped[LoginEvent] = relationship(back_populates="score")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("login_events.id", ondelete="CASCADE"), index=True)
    severity: Mapped[str] = mapped_column(String(16))
    threat_type: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(String(512))
    affected_user: Mapped[str] = mapped_column(String(128))
    source_ip: Mapped[str] = mapped_column(String(64))
    risk: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="open")  # open | ack | closed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    __table_args__ = (Index("ix_alerts_created_status", "created_at", "status"),)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    target: Mapped[str] = mapped_column(String(128))
    detail: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
