"""Health and readiness routes."""

import asyncio
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter()

# ── Startup: fail fast on weak production secrets ──────────────────────────
_WEAK_DEFAULTS = {
    "secret_key": "change-me-in-production",
    "jwt_secret": "change-me-jwt-secret",
    "webhook_secret": "change-me-webhook-secret-32chars!!",
}

if settings.environment == "production":
    for field, weak_value in _WEAK_DEFAULTS.items():
        if getattr(settings, field, "") == weak_value:
            raise RuntimeError(
                f"STARTUP BLOCKED: {field.upper()} is still the default placeholder value. "
                f"Set a strong secret in the Render environment variables before deploying."
            )


class HealthResponse(BaseModel):
    status: str
    version: str


class ReadyResponse(BaseModel):
    status: str
    db: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness probe — always succeeds when the process is running."""
    return HealthResponse(status="ok", version="0.1.0")


@router.get("/ready")
async def readiness_check() -> JSONResponse:
    """
    Readiness probe — checks database connectivity with a 3-second timeout.
    Returns 200 if ready, 503 if the DB is unreachable.
    """
    db_status = "unknown"
    try:
        from app.db.session import engine
        async with asyncio.timeout(3.0):
            async with engine.connect() as conn:
                await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_status = "ok"
        return JSONResponse({"status": "ok", "db": db_status})
    except TimeoutError:
        db_status = "timeout"
    except Exception:
        db_status = "error"

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "not_ready", "db": db_status},
    )
