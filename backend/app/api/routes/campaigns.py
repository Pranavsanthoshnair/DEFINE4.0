"""Campaigns routes — CRUD stubs."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

router = APIRouter()


# ── Schemas (inline until schemas/ module is wired) ─────────────────────────

class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    language: str = "en"
    brief: Optional[str] = None


class CampaignOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    language: str
    status: str
    created_at: datetime


# ── Routes ──────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[CampaignOut])
async def list_campaigns():
    """List all campaigns. (Stub — Supabase integration pending.)"""
    return []


@router.post("/", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
async def create_campaign(payload: CampaignCreate):
    """Create a new campaign. (Stub — Supabase integration pending.)"""
    return CampaignOut(
        id=str(uuid.uuid4()),
        name=payload.name,
        description=payload.description,
        language=payload.language,
        status="draft",
        created_at=datetime.utcnow(),
    )


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(campaign_id: str):
    """Retrieve a single campaign by ID. (Stub.)"""
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(campaign_id: str):
    """Delete a campaign by ID. (Stub.)"""
    return
