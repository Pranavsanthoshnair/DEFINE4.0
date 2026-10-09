"""
Compatibility router — maps /api/* paths used by the frontend api-client.ts
to the same backend handlers as /api/v1/* routes.

This avoids forking the frontend code. All business logic stays in the
original route modules. This file is just path aliases.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes.campaigns import router as campaigns_router
from app.api.routes.contacts import router as contacts_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.health import router as health_router
from app.api.routes.capabilities import router as capabilities_router
from app.api.routes.sessions import router as sessions_router

compat_router = APIRouter()

# /api/campaigns  →  same handlers as /api/v1/campaigns
compat_router.include_router(campaigns_router, prefix="/api/campaigns", tags=["compat-campaigns"])

# /api/contacts
compat_router.include_router(contacts_router, prefix="/api/contacts", tags=["compat-contacts"])

# /api/analytics
compat_router.include_router(analytics_router, prefix="/api/analytics", tags=["compat-analytics"])

# /api/overview  →  single overview summary endpoint
from fastapi import APIRouter as _R
_overview = _R()

from app.db.supabase_client import get_supabase
from pydantic import BaseModel


class Overview(BaseModel):
    total_campaigns: int
    total_contacts: int
    total_calls: int
    calls_answered: int
    calls_failed: int
    callbacks_pending: int
    eligible_for_retry: int


@_overview.get("")
async def get_overview():
    """Dashboard overview — aggregates for the KPI cards."""
    try:
        sb = get_supabase()
        campaigns_resp = sb.table("campaigns").select("id", count="exact").execute()  # type: ignore[arg-type]
        contacts_resp = sb.table("contacts").select("id", count="exact").execute()    # type: ignore[arg-type]
        calls_resp = sb.table("calls").select("status,outcome").execute()
        calls = calls_resp.data or []

        answered = sum(1 for c in calls if c.get("status") == "completed")
        failed = sum(1 for c in calls if c.get("status") in ("failed", "error"))
        callbacks = sum(1 for c in calls if c.get("outcome") == "call_later")
        retry_resp = (
            sb.table("campaign_contacts")
            .select("id", count="exact")  # type: ignore[arg-type]
            .eq("status", "pending")
            .execute()
        )
        return Overview(
            total_campaigns=campaigns_resp.count or 0,
            total_contacts=contacts_resp.count or 0,
            total_calls=len(calls),
            calls_answered=answered,
            calls_failed=failed,
            callbacks_pending=callbacks,
            eligible_for_retry=retry_resp.count or 0,
        )
    except Exception as exc:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=503, detail=f"Database error: {exc}")


compat_router.include_router(_overview, prefix="/api/overview", tags=["compat-overview"])

# /api/sessions  →  browser voice sessions
compat_router.include_router(sessions_router, prefix="/api/sessions", tags=["compat-sessions"])

# /healthz  →  health check
compat_router.include_router(health_router, tags=["compat-health"])
