"""Campaigns routes — CRUD backed by Supabase."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.db.supabase_client import get_supabase, is_supabase_configured

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
    if not is_supabase_configured():
        return []
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
    if not is_supabase_configured():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
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


@router.post("/{campaign_id}/launch", status_code=status.HTTP_202_ACCEPTED)
async def launch_campaign(
    campaign_id: str,
    channel: Optional[str] = None,
    max_contacts: int = 500,
):
    """
    Launch a campaign on the best available channel.

    Channel auto-selection:
      1. Exotel / Twilio (if credentials configured)
      2. Telegram (if TELEGRAM_BOT_TOKEN set)
      3. Browser voice simulator (always available)

    Pass ?channel=telephony|browser|telegram to override.
    """
    from app.services.campaign_engine import run_campaign
    try:
        result = await run_campaign(
            campaign_id=campaign_id,
            channel=channel or "auto",
            max_contacts=max_contacts,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{campaign_id}/channel")
async def get_campaign_channel(campaign_id: str):
    """Return which execution channel would be selected for this campaign."""
    from app.services.campaign_engine import detect_channel
    from app.telephony.providers.factory import active_provider_name
    channel = detect_channel()
    return {
        "campaign_id": campaign_id,
        "selected_channel": channel,
        "telephony_provider": active_provider_name(),
        "telegram_configured": bool(settings.telegram_bot_token),
        "elevenlabs_configured": bool(settings.elevenlabs_api_key),
        "reason": {
            "telephony": "Exotel or Twilio credentials detected",
            "telegram": "TELEGRAM_BOT_TOKEN set, no telephony credentials",
            "browser": "No telephony or Telegram configured — always available",
        }.get(channel, "unknown"),
    }



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


@router.post("/{campaign_id}/prepare-audio", status_code=status.HTTP_202_ACCEPTED)
async def prepare_campaign_audio(
    campaign_id: str,
    voice_id: Optional[str] = None,
    language: Optional[str] = None,
):
    """
    Pre-generate all ElevenLabs TTS audio for a campaign.

    Generates: greeting, prompt, reprompt, all acknowledgements, goodbye, voicemail.
    Stores audio URLs in the campaign row (audio_urls JSONB column).
    Updates campaign status to 'ready'.

    These URLs are served via GET /api/v1/audio/{token} and played
    during live Twilio/Exotel calls — the caller hears ElevenLabs voice,
    NOT the provider's built-in TTS.
    """
    try:
        sb = get_supabase()
        # Fetch campaign
        camp_resp = sb.table(_TABLE).select("id,name,language,status").eq("id", campaign_id).single().execute()
        if not camp_resp.data:
            raise HTTPException(status_code=404, detail="Campaign not found")

        campaign = camp_resp.data
        lang = language or campaign.get("language", "en")
        name = campaign.get("name", "this event")

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}")

    # Generate audio (async — may take 5-15 seconds for 10 segments)
    from app.services.tts_service import generate_campaign_audio
    try:
        audio_urls = await generate_campaign_audio(
            campaign_id=campaign_id,
            campaign_name=name,
            language=lang,
            voice_id=voice_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"TTS generation failed: {exc}. Ensure ELEVENLABS_API_KEY is set.",
        )

    # Persist audio URLs and mark campaign ready
    try:
        sb = get_supabase()
        sb.table(_TABLE).update({
            "audio_urls": audio_urls,
            "status": "ready",
        }).eq("id", campaign_id).execute()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Failed to save audio URLs: {exc}")

    segments_generated = sum(1 for v in audio_urls.values() if v)
    return {
        "campaign_id": campaign_id,
        "status": "ready",
        "segments_generated": segments_generated,
        "total_segments": len(audio_urls),
        "voice": voice_id or "default (Sarah)",
        "language": lang,
        "message": f"Generated {segments_generated}/{len(audio_urls)} audio segments using ElevenLabs. Campaign is ready to call.",
    }
