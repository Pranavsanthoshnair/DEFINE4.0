"""Campaigns routes — CRUD backed by Supabase."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.db.supabase_client import get_supabase, is_supabase_configured

router = APIRouter()

_TABLE = "campaigns"


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    org_name: Optional[str] = Field(None, description="Host organization / client name")
    organization: Optional[str] = None
    description: Optional[str] = None
    language: str = "en"
    languages: Optional[List[str]] = None
    brief: Optional[str] = None
    voice_id: Optional[str] = None
    event_details: Optional[dict] = None
    status: Optional[str] = "draft"
    scheduled_at: Optional[str] = None
    max_retries: Optional[int] = 2


class CampaignOut(BaseModel):
    id: str
    name: str
    org_name: Optional[str] = None
    organization: Optional[str] = None
    description: Optional[str] = None
    language: str = "en"
    languages: Optional[List[str]] = None
    brief: Optional[str] = None
    voice_id: Optional[str] = None
    event_details: Optional[dict] = None
    status: str = "draft"
    contact_count: Optional[int] = 0
    confirmed: Optional[int] = 0
    rate: Optional[str] = None
    created_at: str   # ISO string


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row_to_out(row: dict) -> CampaignOut:
    org = row.get("org_name") or row.get("organization")
    # If not in separate column, check if stored in brief or description
    desc = row.get("description")
    brief = row.get("brief")
    return CampaignOut(
        id=str(row["id"]),
        name=row["name"],
        org_name=org,
        organization=org,
        description=desc,
        language=row.get("language", "en"),
        languages=row.get("languages") or [row.get("language", "en")],
        brief=brief,
        voice_id=row.get("voice_id"),
        event_details=row.get("event_details"),
        status=row.get("status", "draft"),
        contact_count=row.get("contact_count", 0),
        confirmed=row.get("confirmed", 0),
        rate=row.get("rate"),
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
        err_str = str(exc).lower()
        if "invalid api key" in err_str or "apikey" in err_str or "unauthorized" in err_str:
            return []
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
        org = payload.org_name or payload.organization
        desc = payload.description
        if org and not desc:
            desc = f"Organization: {org}"
        elif org and desc and org not in desc:
            desc = f"{desc} | Org: {org}"
            
        brief = payload.brief
        if org and not brief:
            brief = f"Host: {org}"

        row = {
            "id": new_id,
            "name": payload.name,
            "description": desc,
            "language": payload.language,
            "brief": brief,
            "status": payload.status or "draft",
            "created_at": now,
        }
        if payload.scheduled_at:
            row["scheduled_at"] = payload.scheduled_at
        if payload.max_retries is not None:
            row["max_retries"] = payload.max_retries

        resp = sb.table(_TABLE).insert(row).execute()
        if not resp.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Campaign insert returned no data.",
            )
        out = _row_to_out(resp.data[0])
        if org:
            out.org_name = org
            out.organization = org
        return out
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
    from app.services.campaign_engine import run_campaign, Channel
    from typing import cast
    try:
        result = await run_campaign(
            campaign_id=campaign_id,
            channel=cast("Channel", channel or "auto"),
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



@router.post("/{campaign_id}/stop", status_code=status.HTTP_200_OK)
async def stop_campaign(campaign_id: str):
    """
    Stop / de-launch a running campaign.
    Sets status back to 'paused' so it can be relaunched later.
    """
    try:
        sb = get_supabase()
        now = datetime.now(timezone.utc).isoformat()
        resp = (
            sb.table(_TABLE)
            .update({"status": "paused", "updated_at": now})
            .eq("id", campaign_id)
            .execute()
        )
        if not resp.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
        return {"campaign_id": campaign_id, "status": "paused"}
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
    # audio_urls is stored as a JSON string in the 'brief' field if the
    # audio_urls column doesn't exist yet — add it via Supabase SQL editor:
    #   ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS audio_urls JSONB;
    try:
        sb = get_supabase()
        update_payload: dict = {"status": "ready"}
        try:
            sb.table(_TABLE).update({**update_payload, "audio_urls": audio_urls}).eq("id", campaign_id).execute()
        except Exception:
            # audio_urls column not yet added — store URLs serialised in brief as fallback
            import json as _json
            sb.table(_TABLE).update({
                **update_payload,
                "brief": _json.dumps({"audio_urls": audio_urls}),
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
