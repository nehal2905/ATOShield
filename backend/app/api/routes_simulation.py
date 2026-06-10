# NOTE: Do NOT add `from __future__ import annotations` here. This endpoint is
# wrapped by slowapi's @limiter.limit; stringized annotations would be resolved
# against slowapi's module globals and raise PydanticUndefinedAnnotation for
# "SimulateIn" on FastAPI/Pydantic <=0.111/<=2.7. Real annotations avoid it.
from fastapi import APIRouter, Depends, Request

from app.config import settings
from app.core import pipeline
from app.deps import CurrentUser, get_current_user, limiter
from app.schemas.events import SimulateIn, SimulateOut

router = APIRouter(prefix="/api", tags=["simulation"])


@router.post("/simulate", response_model=SimulateOut)
@limiter.limit(settings.rate_limit_simulate)
async def simulate(
    request: Request,
    body: SimulateIn,
    current: CurrentUser = Depends(get_current_user),
):
    """Score a manually-specified event (no persistence). Returns a full trace.

    The score comes from the real Isolation Forest — NOT a client-side heuristic.
    """
    return await pipeline.process_simulation(body)
