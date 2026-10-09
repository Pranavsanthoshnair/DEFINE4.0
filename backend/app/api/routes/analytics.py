"""Analytics routes — aggregate stats stub."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class CampaignStats(BaseModel):
    campaign_id: str
    total_recipients: int
    calls_attempted: int
    calls_answered: int
    calls_failed: int
    completion_rate: float


@router.get("/{campaign_id}", response_model=CampaignStats)
async def get_campaign_analytics(campaign_id: str):
    """
    Return aggregate analytics for a campaign.
    (Stub — Supabase aggregation pending.)
    """
    return CampaignStats(
        campaign_id=campaign_id,
        total_recipients=0,
        calls_attempted=0,
        calls_answered=0,
        calls_failed=0,
        completion_rate=0.0,
    )
