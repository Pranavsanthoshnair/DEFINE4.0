"""Analytics API backed by the SQLAlchemy call model."""

from __future__ import annotations

import uuid

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


@router.get("/{campaign_id}")
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
        # Analytics must read the same Supabase data used by campaigns and
        # contacts.  The SQLAlchemy store is only used by the worker model and
        # is empty in the Supabase deployment.
        sb = __import__("app.db.supabase_client", fromlist=["get_supabase"]).get_supabase()
        campaign = sb.table("campaigns").select("id,name").eq("id", campaign_id).single().execute().data or {}
        if not campaign:
            raise ValueError("campaign not found")
        links = sb.table("campaign_contacts").select("status,outcome").eq("campaign_id", campaign_id).execute().data or []
        outcomes = [str(r.get("outcome") or r.get("status") or "pending") for r in links]
        completed = sum(o in {"confirmed", "declined", "call_later", "completed"} for o in outcomes)
        failed = sum(o in {"failed", "no_answer", "busy", "exhausted", "skipped"} for o in outcomes)
        total = len(links)
        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign.get("name", ""),
            "total": total,
            "total_recipients": total,
            "calls_attempted": completed + failed,
            "calls_answered": completed,
            "calls_failed": failed,
            "calls_pending": max(total - completed - failed, 0),
            "completion_rate": (completed + failed) / total if total else 0,
            "answer_rate": completed / total if total else 0,
            "outcomes": {key: outcomes.count(key) for key in ("confirmed", "declined", "call_later", "pending", "failed", "no_answer")},
            "by_language": [],
            "by_day": [],
        }
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid campaign id")
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
