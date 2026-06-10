## NOTE: Do NOT add `from __future__ import annotations` here. These endpoints are
# wrapped by slowapi's @limiter.limit, whose wrapper carries slowapi's module
# globals. With stringized annotations, FastAPI/Pydantic (esp. <=0.111/<=2.7)
# would try to resolve "LoginEventIn" against slowapi's globals and fail with
# PydanticUndefinedAnnotation. Keeping annotations as real objects avoids that.
from typing import List

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import pipeline
from app.db import crud
from app.deps import CurrentUser, get_current_user, get_db, limiter
from app.schemas.events import LoginEventIn, ScoredEventOut

router = APIRouter(prefix="/api", tags=["events"])


@router.post("/events", response_model=ScoredEventOut)
@limiter.limit(settings.rate_limit_events)
async def ingest_event(
    request: Request,
    body: LoginEventIn,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """Ingest one login event: score -> persist -> broadcast -> return result."""
    return await pipeline.process_login_event(db, body)


@router.get("/events", response_model=List[ScoredEventOut])
async def recent_events(
    limit: int = Query(default=30, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    events = await crud.list_recent_events(db, limit=limit)
    out: List[ScoredEventOut] = []
    for e in events:
        rf = e.raw_features or {}
        s = e.score
        out.append(ScoredEventOut(
            id=e.id,
            user=e.user_ref,
            ip=e.ip,
            device_fp=e.device_fp,
            geo_lat=e.geo_lat,
            geo_lon=e.geo_lon,
            timestamp=e.timestamp,
            login_hour=e.login_hour,
            frequency=e.frequency,
            failed_attempts=e.failed_attempts,
            ip_change=float(rf.get("ip_change", 0)),
            device_change=float(rf.get("device_change", 0)),
            geo_velocity=float(rf.get("geo_velocity", 0)),
            impossible_travel=float(rf.get("geo_velocity", 0)) > 900,
            raw_score=s.raw_score if s else 0.0,
            risk=s.risk if s else 0,
            tier=s.tier if s else "LOW",
            action="",
            contributions=(s.contributions if s else {}) or {},
        ))
    return out
