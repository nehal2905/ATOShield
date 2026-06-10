from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.deps import CurrentUser, get_current_user, get_db

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
async def stats(
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await crud.get_stats(db)
