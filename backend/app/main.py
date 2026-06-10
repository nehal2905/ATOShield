"""ATOShield FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import (
    routes_alerts,
    routes_auth,
    routes_events,
    routes_simulation,
    routes_stats,
)
from app.config import settings
from app.core.security import decode_token, hash_password
from app.core.scorer import Scorer, set_scorer
from app.db import crud
from app.db.session import SessionLocal, init_db
from app.deps import limiter
from app.ws.manager import manager

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
log = logging.getLogger("atoshield")


async def _bootstrap_admin() -> None:
    async with SessionLocal() as db:
        existing = await crud.get_user_by_username(db, settings.bootstrap_admin_username)
        if existing is None:
            await crud.create_user(
                db,
                settings.bootstrap_admin_username,
                hash_password(settings.bootstrap_admin_password),
                role="admin",
            )
            log.info("Bootstrapped admin user '%s'", settings.bootstrap_admin_username)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _bootstrap_admin()
    try:
        set_scorer(Scorer().load())
        log.info("Scorer loaded from %s", settings.ml_artifacts_dir)
    except FileNotFoundError as exc:
        log.error("ML artifacts not found: %s", exc)  # API boots; scoring returns 503
    except Exception as exc:  # e.g. sklearn/numpy version mismatch unpickling the model
        log.error(
            "ML artifacts failed to load (version mismatch?): %s. "
            "Retrain with the pinned versions so the model matches the runtime.",
            exc,
        )
    await manager.start_pubsub()
    yield
    await manager.stop_pubsub()


app = FastAPI(title="ATOShield API", version="1.0.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_auth.router)
app.include_router(routes_events.router)
app.include_router(routes_simulation.router)
app.include_router(routes_alerts.router)
app.include_router(routes_stats.router)


@app.get("/api/health")
async def health():
    from app.core.scorer import _scorer
    return {"status": "ok", "model_loaded": _scorer is not None and _scorer.ready}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str | None = None):
    # Authenticate via ?token= query param or the httpOnly access_token cookie.
    auth = token or ws.cookies.get("access_token")
    if not auth or not decode_token(auth):
        await ws.close(code=1008)  # policy violation
        return
    await manager.connect(ws)
    try:
        while True:
            # We don't expect client messages; keep the socket alive.
            await ws.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(ws)
    except Exception:
        await manager.disconnect(ws)
