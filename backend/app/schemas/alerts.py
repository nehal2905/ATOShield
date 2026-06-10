from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    severity: str
    threat_type: str
    description: str
    affected_user: str
    source_ip: str
    risk: int
    status: str
    created_at: datetime


class AlertUpdate(BaseModel):
    status: str = Field(pattern="^(open|ack|closed)$")
