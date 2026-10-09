"""Analytics routes — real aggregates from Supabase."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.db.supabase_client import get_supabase, is_supabase_configured

router = APIRouter()


class CampaignStats(BaseModel):
    campaign_id: str
    total_recipients: int
    calls_attempted: int
    calls_answered: int
    calls_failed: int
    calls_pending: int
    completion_rate: float
    answer_rate: float


@router.get("/{campaign_id}", response_model=CampaignStats)
async def get_campaign_analytics(campaign_id: str):
    """
    Return aggregate call statistics for a campaign.
    Computed live from campaign_contacts and calls tables.
    """
    if not is_supabase_configured():
        return CampaignStats(
            campaign_id=campaign_id,
            total_recipients=0,
            calls_attempted=0,
            calls_answered=0,
            calls_failed=0,
            calls_pending=0,
            completion_rate=0.0,
            answer_rate=0.0,
        )
    try:
        sb = get_supabase()

        # Total recipients in campaign
        recipients_resp = (
            sb.table("campaign_contacts")
            .select("id", count="exact")
            .eq("campaign_id", campaign_id)
            .execute()
        )
        total = recipients_resp.count or 0

        # Calls per outcome status
        calls_resp = (
            sb.table("calls")
            .select("status")
            .eq("campaign_id", campaign_id)
            .execute()
        )
        calls = calls_resp.data or []
        attempted = len(calls)
        answered = sum(1 for c in calls if c.get("status") in ("completed", "busy", "no_answer"))
        failed = sum(1 for c in calls if c.get("status") in ("failed", "error", "cancelled"))
        pending = sum(1 for c in calls if c.get("status") in ("queued", "in_progress", "ringing"))

        completion_rate = round(attempted / total, 4) if total else 0.0
        answer_rate = round(answered / attempted, 4) if attempted else 0.0

        return CampaignStats(
            campaign_id=campaign_id,
            total_recipients=total,
            calls_attempted=attempted,
            calls_answered=answered,
            calls_failed=failed,
            calls_pending=pending,
            completion_rate=completion_rate,
            answer_rate=answer_rate,
        )
    except HTTPException:
        raise
    except Exception as exc:
        err_str = str(exc).lower()
        if "invalid api key" in err_str or "apikey" in err_str or "unauthorized" in err_str:
            return CampaignStats(
                campaign_id=campaign_id,
                total_recipients=0, calls_attempted=0, calls_answered=0,
                calls_failed=0, calls_pending=0, completion_rate=0.0, answer_rate=0.0,
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database error: {exc}",
        )


@router.get("/overview/summary")
async def get_overview_summary():
    """
    Overall platform summary — total campaigns, contacts, calls made.
    Used by the dashboard overview page.
    """
    if not is_supabase_configured():
        return {
            "total_campaigns": 0,
            "total_contacts": 0,
            "total_calls": 0,
            "calls_answered": 0,
            "calls_failed": 0,
        }
    try:
        sb = get_supabase()

        campaigns_resp = sb.table("campaigns").select("id", count="exact").execute()
        contacts_resp = sb.table("contacts").select("id", count="exact").execute()
        calls_resp = sb.table("calls").select("status").execute()
        calls = calls_resp.data or []

        return {
            "total_campaigns": campaigns_resp.count or 0,
            "total_contacts": contacts_resp.count or 0,
            "total_calls": len(calls),
            "calls_answered": sum(1 for c in calls if c.get("status") == "completed"),
            "calls_failed": sum(1 for c in calls if c.get("status") in ("failed", "error")),
        }
    except Exception as exc:
        err_str = str(exc).lower()
        if "invalid api key" in err_str or "apikey" in err_str or "unauthorized" in err_str:
            return {"total_campaigns": 0, "total_contacts": 0, "total_calls": 0, "calls_answered": 0, "calls_failed": 0}
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database error: {exc}",
        )
