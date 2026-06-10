"""Shared FastAPI dependencies: DB session, auth, rate limiting."""

from __future__ import annotations

from typing import Optional

from fastapi import Cookie, Depends, Header, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.core.security import decode_token
from app.db.session import get_db  # re-exported for routers

# Shared rate limiter (configured in main.py with the app)
limiter = Limiter(key_func=get_remote_address)


class CurrentUser:
    def __init__(self, username: str, role: str) -> None:
        self.username = username
        self.role = role


def _extract_token(authorization: Optional[str], access_token: Optional[str]) -> Optional[str]:
    # Prefer the httpOnly cookie; fall back to Authorization: Bearer <token>.
    if access_token:
        return access_token
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return None


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
    access_token: Optional[str] = Cookie(default=None),
) -> CurrentUser:
    token = _extract_token(authorization, access_token)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return CurrentUser(username=payload["sub"], role=payload.get("role", "analyst"))


__all__ = ["get_db", "get_current_user", "CurrentUser", "limiter", "settings"]
