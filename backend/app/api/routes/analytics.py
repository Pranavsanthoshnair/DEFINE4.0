"""Analytics API backed by the SQLAlchemy call model."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Call, Campaign, CampaignContact, Contact
from app.db.session import get_db
from app.services.analytics_service import AnalyticsService

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
        raise HTTPException(status_code=503, detail=f"Database error: {exc}")


@router.get("/{campaign_id}/recipients/{recipient_id}")
async def get_recipient_history(campaign_id: str, recipient_id: str):
    try:
        return {
            "campaign_id": campaign_id,
            "recipient_id": recipient_id,
            "calls": await AnalyticsService().get_recipient_history(recipient_id),
        }
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid id")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}")


@router.get("/overview/summary")
async def get_overview_summary(db: AsyncSession = Depends(get_db)):
    campaigns = await db.scalar(select(func.count()).select_from(Campaign)) or 0
    contacts = await db.scalar(select(func.count()).select_from(Contact)) or 0
    calls = await db.scalar(select(func.count()).select_from(Call)) or 0
    answered = await db.scalar(select(func.count()).select_from(Call).where(
        Call.status == "completed")) or 0
    failed = await db.scalar(select(func.count()).select_from(Call).where(
        Call.status.in_(["failed", "busy", "no_answer", "canceled"]))) or 0
    return {
        "total_campaigns": int(campaigns),
        "total_contacts": int(contacts),
        "total_calls": int(calls),
        "calls_answered": int(answered),
        "calls_failed": int(failed),
    }
