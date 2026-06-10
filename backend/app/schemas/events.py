#from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class LoginEventIn(BaseModel):
    """A real(istic) login event. Baseline-derived signals are computed server-side."""

    user: str = Field(min_length=1, max_length=128)
    ip: str = Field(min_length=3, max_length=64)
    device_fp: str = Field(min_length=1, max_length=128)
    geo_lat: float = Field(ge=-90, le=90)
    geo_lon: float = Field(ge=-180, le=180)
    timestamp: Optional[datetime] = None
    success: bool = True
    # Optional explicit override for failed attempts (the synthetic generator uses it).
    failed_attempts: Optional[int] = Field(default=None, ge=0, le=1000)


class SimulateIn(BaseModel):
    """Manual scoring: the six raw features straight from the UI sliders."""

    login_hour: float = Field(ge=0, le=24)
    ip_change: float = Field(ge=0, le=1)
    device_change: float = Field(ge=0, le=1)
    frequency: float = Field(ge=0, le=1000)
    geo_velocity: float = Field(ge=0, le=5000)
    failed_attempts: float = Field(ge=0, le=1000)


class ScoredEventOut(BaseModel):
    id: Optional[int] = None
    user: str
    ip: str
    device_fp: str
    geo_lat: float
    geo_lon: float
    timestamp: datetime
    login_hour: float
    frequency: float
    failed_attempts: float
    ip_change: float
    device_change: float
    geo_velocity: float
    impossible_travel: bool
    raw_score: float
    risk: int
    tier: str
    action: str
    contributions: Dict[str, float]
    alert_id: Optional[int] = None
    threat_type: Optional[str] = None


class PipelineStep(BaseModel):
    step: str
    detail: str
    data: Optional[dict] = None


class SimulateOut(BaseModel):
    result: ScoredEventOut
    trace: List[PipelineStep]
