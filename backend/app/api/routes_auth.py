from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db import crud
from app.deps import CurrentUser, get_current_user, get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_auth_cookie(response: Response, token: str) -> None:
    # httpOnly so JS can't read it (XSS-resistant). samesite=lax for normal nav.
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.app_env != "development",
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    user = await crud.get_user_by_username(db, body.username)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(subject=user.username, role=user.role)
    _set_auth_cookie(response, token)
    await crud.add_audit(db, actor=user.username, action="login", target=user.username, detail={})
    return TokenResponse(access_token=token, username=user.username, role=user.role)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if await crud.get_user_by_username(db, body.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    user = await crud.create_user(db, body.username, hash_password(body.password), body.role)
    return UserOut(id=user.id, username=user.username, role=user.role)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user = await crud.get_user_by_username(db, current.username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut(id=user.id, username=user.username, role=user.role)
