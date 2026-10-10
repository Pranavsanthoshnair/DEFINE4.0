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
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import User
from app.db.session import get_db
from app.db.supabase_client import get_supabase, is_supabase_configured

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Password hashing (PBKDF2-HMAC-SHA256 with constant-time verification)
# ---------------------------------------------------------------------------
import hashlib
import hmac
import secrets


def get_password_hash(password: str) -> str:
    """Return a secure PBKDF2-HMAC-SHA256 hash of ``password``."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"pbkdf2:sha256:100000${salt}${key.hex()}"


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if ``plain`` matches the ``hashed`` value."""
    if hashed.startswith("pbkdf2:sha256:"):
        try:
            parts = hashed.split("$")
            if len(parts) == 3:
                salt = parts[1]
                expected_key_hex = parts[2]
                key = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt.encode("utf-8"), 100_000)
                return hmac.compare_digest(key.hex(), expected_key_hex)
        except Exception:
            return False

    # Also support plain sha256 or bcrypt if stored from seed
    try:
        if hashed.startswith("$argon2") or hashed.startswith("$2b$") or hashed.startswith("$2a$"):
            _ctx = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")
            return _ctx.verify(plain, hashed)
    except Exception:
        pass

    return False


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

# ---------------------------------------------------------------------------
# In-memory user cache + seed
# ---------------------------------------------------------------------------
_users_by_email: dict[str, dict[str, Any]] = {}
_users_by_id: dict[str, dict[str, Any]] = {}


def _seed_admin_if_needed():
    admin_email = (settings.admin_email or "admin@veylo.internal").lower()
    if admin_email not in _users_by_email:
        admin_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, admin_email))
        record = {
            "id": admin_id,
            "email": admin_email,
            "password_hash": get_password_hash(settings.admin_password or "dev-admin-pass"),
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _users_by_email[admin_email] = record
        _users_by_id[admin_id] = record


_seed_admin_if_needed()


async def _find_user_by_email(email: str, db: AsyncSession | None = None) -> dict[str, Any] | None:
    """Find user record by email across in-memory cache, Supabase REST, or direct DB."""
    email_clean = email.strip().lower()
    _seed_admin_if_needed()

    # 1. In-memory cache
    if email_clean in _users_by_email:
        return _users_by_email[email_clean]

    # 2. Supabase REST
    if is_supabase_configured():
        try:
            sb = get_supabase()
            resp = sb.table("users").select("*").eq("email", email_clean).limit(1).execute()
            if resp.data and len(resp.data) > 0:
                row = resp.data[0]
                _users_by_email[email_clean] = row
                _users_by_id[str(row["id"])] = row
                return row
        except Exception as e:
            log.debug("supabase_user_lookup_error", error=str(e))

    # 3. Direct DB session
    if db:
        try:
            result = await db.execute(select(User).where(User.email == email_clean))
            user = result.scalar_one_or_none()
            if user:
                row = {
                    "id": str(user.id),
                    "email": user.email,
                    "password_hash": user.password_hash,
                    "role": user.role,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                }
                _users_by_email[email_clean] = row
                _users_by_id[str(user.id)] = row
                return row
        except Exception as e:
            log.debug("db_user_lookup_error", error=str(e))

    return None


async def _find_user_by_id(user_id: str, db: AsyncSession | None = None) -> dict[str, Any] | None:
    """Find user record by user ID across in-memory cache, Supabase REST, or direct DB."""
    _seed_admin_if_needed()

    # 1. In-memory cache
    if user_id in _users_by_id:
        return _users_by_id[user_id]

    # 2. Supabase REST
    if is_supabase_configured():
        try:
            sb = get_supabase()
            resp = sb.table("users").select("*").eq("id", user_id).limit(1).execute()
            if resp.data and len(resp.data) > 0:
                row = resp.data[0]
                _users_by_email[row["email"].lower()] = row
                _users_by_id[user_id] = row
                return row
        except Exception as e:
            log.debug("supabase_user_id_lookup_error", error=str(e))

    # 3. Direct DB session
    if db:
        try:
            result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
            user = result.scalar_one_or_none()
            if user:
                row = {
                    "id": str(user.id),
                    "email": user.email,
                    "password_hash": user.password_hash,
                    "role": user.role,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                }
                _users_by_email[user.email.lower()] = row
                _users_by_id[user_id] = row
                return row
        except Exception as e:
            log.debug("db_user_id_lookup_error", error=str(e))

    return None


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

    user_data = await _find_user_by_id(user_id, db)
    if user_data is None:
        raise credentials_exception

    return User(
        id=uuid.UUID(user_data["id"]),
        email=user_data["email"],
        password_hash=user_data["password_hash"],
        role=user_data.get("role", "organiser"),
    )


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
    email: str
    password: str


class SignupRequest(BaseModel):
    email: str
    password: str
    role: str = "organiser"


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


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    request: Request,
    body: SignupRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Register a new user account with email and password."""
    ip = request.client.host if request.client else "unknown"
    _check_rate_limit(ip)

    email_clean = body.email.strip().lower()
    if not email_clean or "@" not in email_clean or "." not in email_clean:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "invalid_email", "message": "Please enter a valid email address."}},
        )

    if len(body.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "password_too_short", "message": "Password must be at least 6 characters long."}},
        )

    # Check if user already exists
    existing = await _find_user_by_email(email_clean, db)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "email_exists", "message": "An account with this email already exists."}},
        )

async def _save_user(
    email: str,
    password_hash: str,
    role: str = "organiser",
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """Persist user to Supabase/PostgreSQL, failing loudly in production if DB is unavailable."""
    email_clean = email.strip().lower()
    user_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    user_record = {
        "id": user_id,
        "email": email_clean,
        "password_hash": password_hash,
        "role": role,
        "created_at": now_iso,
    }

    db_success = False
    supabase_err = None
    db_err = None

    if is_supabase_configured():
        try:
            sb = get_supabase()
            sb.table("users").insert(user_record).execute()
            db_success = True
        except Exception as e:
            supabase_err = e
            log.warning("supabase_user_insert_error", error=str(e))

    if db:
        try:
            new_user = User(
                id=uuid.UUID(user_id),
                email=email_clean,
                password_hash=password_hash,
                role=role,
            )
            db.add(new_user)
            await db.commit()
            db_success = True
        except Exception as e:
            db_err = e
            log.warning("db_user_insert_error", error=str(e))

    # In production, never fallback silently to in-memory state
    if settings.environment == "production" and not db_success:
        log.error("production_db_unavailable", supabase_err=str(supabase_err), db_err=str(db_err))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": {"code": "database_unavailable", "message": "Database unavailable in production. Memory fallback is disabled."}},
        )

    # Store in memory for dev / caching
    _users_by_email[email_clean] = user_record
    _users_by_id[user_id] = user_record
    return user_record


@router.post("/signup", response_model=TokenResponse)
async def signup(
    request: Request,
    body: SignupRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Create a new user account with secure password hashing.

    In production, this strictly requires persistent database storage.
    """
    ip = request.client.host if request.client else "unknown"
    _check_rate_limit(ip)

    email_clean = body.email.strip().lower()
    existing = await _find_user_by_email(email_clean, db)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "email_exists", "message": "An account with this email already exists."}},
        )

    user_role = body.role if body.role in ("admin", "organiser") else "organiser"
    hashed_pwd = get_password_hash(body.password)

    user_record = await _save_user(
        email=email_clean,
        password_hash=hashed_pwd,
        role=user_role,
        db=db,
    )
    user_id = user_record["id"]

    token = create_access_token({"sub": user_id})
    log.info("signup_ok", user_id=user_id, role=user_role, email=email_clean)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user={"id": user_id, "email": email_clean, "role": user_role},
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

    email_clean = body.email.strip().lower()
    user = await _find_user_by_email(email_clean, db)

    # Constant-time: always attempt verification even on unknown email
    dummy_hash = "$argon2id$v=19$m=65536,t=3,p=4$qH1x5yY9M5q5u4zT3J7eQA$qG1x5yY9M5q5u4zT3J7eQAqH1x5yY9M5q5u4zT3J7eQA"
    stored_hash = user["password_hash"] if user else dummy_hash
    password_ok = verify_password(body.password, stored_hash)

    if user is None or not password_ok:
        log.info("login_failed", ip=ip)
        raise _GENERIC_LOGIN_ERROR

    token = create_access_token({"sub": str(user["id"])})
    log.info("login_ok", user_id=str(user["id"]), role=user["role"])
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user={"id": str(user["id"]), "email": user["email"], "role": user["role"]},
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
