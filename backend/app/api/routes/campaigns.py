"""Campaigns routes — CRUD backed by Supabase."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.db.supabase_client import get_supabase

router = APIRouter()

_TABLE = "campaigns"


# ── Schemas ──────────────────────────────────────────────────────────────────

class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    language: str = "en"
    brief: Optional[str] = None


class CampaignOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    language: str
    status: str
    created_at: str   # ISO string — Supabase returns strings


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row_to_out(row: dict) -> CampaignOut:
    return CampaignOut(
        id=str(row["id"]),
        name=row["name"],
        description=row.get("description"),
        language=row.get("language", "en"),
        status=row.get("status", "draft"),
        created_at=str(row.get("created_at", "")),
    )


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[CampaignOut])
async def list_campaigns(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List campaigns with pagination."""
    try:
        sb = get_supabase()
        resp = (
            sb.table(_TABLE)
            .select("id,name,description,language,status,created_at")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return [_row_to_out(r) for r in (resp.data or [])]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database error: {exc}",
        )


@router.post("/", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
async def create_campaign(payload: CampaignCreate):
    """Create a new campaign."""
    try:
        sb = get_supabase()
        new_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "id": new_id,
            "name": payload.name,
            "description": payload.description,
            "language": payload.language,
            "brief": payload.brief,
            "status": "draft",
            "created_at": now,
        }
        resp = sb.table(_TABLE).insert(row).execute()
        if not resp.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Campaign insert returned no data.",
            )
        return _row_to_out(resp.data[0])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database error: {exc}",
        )


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(campaign_id: str):
    """Retrieve a single campaign by ID."""
    try:
        sb = get_supabase()
        resp = (
            sb.table(_TABLE)
            .select("id,name,description,language,status,created_at")
            .eq("id", campaign_id)
            .single()
            .execute()
        )
        if not resp.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
        return _row_to_out(resp.data)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database error: {exc}",
        )


@router.patch("/{campaign_id}", response_model=CampaignOut)
async def update_campaign(campaign_id: str, payload: CampaignCreate):
    """Update campaign fields."""
    try:
        sb = get_supabase()
        updates = payload.model_dump(exclude_none=True)
        resp = (
            sb.table(_TABLE)
            .update(updates)
            .eq("id", campaign_id)
            .execute()
        )
        if not resp.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
        return _row_to_out(resp.data[0])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database error: {exc}",
        )


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(campaign_id: str):
    """Delete a campaign by ID."""
    try:
        sb = get_supabase()
        sb.table(_TABLE).delete().eq("id", campaign_id).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database error: {exc}",
        )
