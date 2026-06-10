from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.deps import CurrentUser, get_current_user, get_db
from app.schemas.alerts import AlertOut, AlertUpdate

router = APIRouter(prefix="/api", tags=["alerts"])


@router.get("/alerts", response_model=List[AlertOut])
async def list_alerts(
    status: Optional[str] = Query(default=None, pattern="^(open|ack|closed)$"),
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    alerts = await crud.list_alerts(db, status=status)
    return [AlertOut.model_validate(a) for a in alerts]


@router.patch("/alerts/{alert_id}", response_model=AlertOut)
async def update_alert(
    alert_id: int,
    body: AlertUpdate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    alert = await crud.update_alert_status(db, alert_id, body.status)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    await crud.add_audit(
        db, actor=current.username, action="alert_status",
        target=str(alert_id), detail={"status": body.status},
    )
    return AlertOut.model_validate(alert)
