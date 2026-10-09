"""
Authentication helpers and FastAPI router.

Implements:
  - Bcrypt password hashing via passlib
  - JWT HS256 token creation (12-hour expiry)
  - FastAPI dependency ``get_current_user``
  - Role-guard dependency ``require_role``
  - POST /api/auth/login
  - GET  /api/auth/me
  - In-memory rate limiter (5 attempts / minute / IP) — Redis-backed in Phase 5
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import jwt
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import User
from app.db.session import get_db

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
_pwd_ctx = CryptContext(schemes=["argon2"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """Return a argon2 hash of ``password``."""
    return _pwd_ctx.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if ``plain`` matches the bcrypt ``hashed`` value."""
    return _pwd_ctx.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_HOURS = 12


def create_access_token(data: dict[str, Any]) -> str:
    """Create a signed JWT with a 12-hour expiry."""
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=_ACCESS_TOKEN_EXPIRE_HOURS)
    payload["exp"] = expire
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


# ---------------------------------------------------------------------------
# OAuth2 scheme
# ---------------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ---------------------------------------------------------------------------
# In-memory rate limiter (dev-mode; Redis in Phase 5)
# ---------------------------------------------------------------------------
# Stores {ip: [timestamps_of_recent_attempts]}
_rate_limit_store: dict[str, list[float]] = defaultdict(list)
_RATE_WINDOW_SEC = 60
_RATE_MAX_ATTEMPTS = 5


def _check_rate_limit(ip: str) -> None:
    now = time.monotonic()
    attempts = _rate_limit_store[ip]
    # Evict old entries
    _rate_limit_store[ip] = [t for t in attempts if now - t < _RATE_WINDOW_SEC]
    if len(_rate_limit_store[ip]) >= _RATE_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": {"code": "rate_limited", "message": "Too many login attempts. Try again later."}},
        )
    _rate_limit_store[ip].append(now)


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Decode the bearer JWT and return the authenticated User row."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": {"code": "invalid_token", "message": "Could not validate credentials."}},
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "token_expired", "message": "Token has expired."}},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


def require_role(role: str):
    """Return a FastAPI dependency that enforces ``role`` membership."""

    async def _dependency(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "forbidden", "message": f"Role '{role}' required."}},
            )
        return current_user

    return _dependency


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict[str, Any]


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/api/auth", tags=["auth"])

_GENERIC_LOGIN_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"error": {"code": "invalid_credentials", "message": "Invalid email or password."}},
    headers={"WWW-Authenticate": "Bearer"},
)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Authenticate with email and password; returns a JWT bearer token.

    Login failures return the same message for unknown email AND wrong password
    to prevent user-enumeration attacks.
    """
    ip = request.client.host if request.client else "unknown"
    _check_rate_limit(ip)

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Constant-time: always attempt verification even on unknown email
    # An argon2 dummy hash
    dummy_hash = "$argon2id$v=19$m=65536,t=3,p=4$qH1x5yY9M5q5u4zT3J7eQA$qG1x5yY9M5q5u4zT3J7eQAqH1x5yY9M5q5u4zT3J7eQA"
    stored_hash = user.password_hash if user else dummy_hash
    password_ok = verify_password(body.password, stored_hash)

    if user is None or not password_ok:
        log.info("login_failed", ip=ip)
        raise _GENERIC_LOGIN_ERROR

    token = create_access_token({"sub": str(user.id)})
    log.info("login_ok", user_id=str(user.id), role=user.role)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user={"id": str(user.id), "email": user.email, "role": user.role},
    )


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Return the authenticated user's profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
    )
