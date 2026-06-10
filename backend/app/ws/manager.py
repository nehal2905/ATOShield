"""WebSocket connection registry + broadcast, backed by Redis pub/sub.

Why Redis pub/sub: with more than one backend replica, an event scored on
replica A must reach dashboard sockets connected to replica B. Each replica
publishes to a shared channel and every replica forwards channel messages to its
local sockets. On a single instance it still works (publish -> subscribe loop).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Set

from fastapi import WebSocket

from app.cache.baseline import get_redis

log = logging.getLogger("atoshield.ws")

CHANNEL = "atoshield:broadcast"


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._pubsub_task: asyncio.Task | None = None

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)
        log.info("ws connected (total=%d)", len(self._connections))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(ws)
        log.info("ws disconnected (total=%d)", len(self._connections))

    async def _send_local(self, message: Dict[str, Any]) -> None:
        text = json.dumps(message, default=str)
        dead = []
        for ws in list(self._connections):
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)

    async def publish(self, message: Dict[str, Any]) -> None:
        """Publish to all replicas via Redis. Falls back to local-only on error."""
        try:
            await get_redis().publish(CHANNEL, json.dumps(message, default=str))
        except Exception:
            log.warning("redis publish failed; broadcasting locally only", exc_info=True)
            await self._send_local(message)

    async def start_pubsub(self) -> None:
        if self._pubsub_task is None:
            self._pubsub_task = asyncio.create_task(self._pubsub_loop())

    async def stop_pubsub(self) -> None:
        if self._pubsub_task:
            self._pubsub_task.cancel()
            self._pubsub_task = None

    async def _pubsub_loop(self) -> None:
        try:
            pubsub = get_redis().pubsub()
            await pubsub.subscribe(CHANNEL)
            async for raw in pubsub.listen():
                if raw is None or raw.get("type") != "message":
                    continue
                try:
                    message = json.loads(raw["data"])
                except (ValueError, TypeError):
                    continue
                await self._send_local(message)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.error("pubsub loop crashed", exc_info=True)


manager = ConnectionManager()
