"""
Campaign Execution Engine
==========================
One engine, three channels. Channel selected automatically based on available credentials.

Channel priority:
  1. TELEPHONY  (Exotel → Twilio → Mock)   CALL_PROVIDER=auto|exotel|twilio
  2. BROWSER    (always available, demo/sim)
  3. TELEGRAM   (if TELEGRAM_BOT_TOKEN set)

All channels:
  - Share the same execution_sessions table
  - Use the same unified intent pipeline (intent_service.py)
  - Use ElevenLabs voice for all audio (telephony + browser TTS)
  - Mark is_simulation=True for browser, False for telephony/Telegram

Usage:
  from app.services.campaign_engine import run_campaign
  await run_campaign(campaign_id="...", channel="auto")
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

import httpx
import structlog

from app.core.config import settings
from app.db.supabase_client import get_supabase
from app.telephony.providers.factory import active_provider_name, get_provider

log = structlog.get_logger()

Channel = Literal["auto", "telephony", "browser", "telegram"]

_EXEC_TABLE = "execution_sessions"
_CAMP_TABLE = "campaigns"
_CONTACTS_TABLE = "campaign_contacts"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Channel detection ─────────────────────────────────────────────────────────

def detect_channel() -> str:
    """
    Auto-select the best available execution channel.
    Returns one of: 'telephony', 'browser', 'telegram'
    """
    provider = active_provider_name()
    if provider in ("exotel", "twilio"):
        return "telephony"
    if settings.telegram_bot_token:
        return "telegram"
    return "browser"


# ── Database helpers ──────────────────────────────────────────────────────────

def _get_campaign(campaign_id: str) -> dict:
    sb = get_supabase()
    resp = sb.table(_CAMP_TABLE).select("*").eq("id", campaign_id).single().execute()
    if not resp.data:
        raise ValueError(f"Campaign {campaign_id} not found")
    return resp.data


def _get_contacts(campaign_id: str, limit: int = 500) -> list[dict]:
    sb = get_supabase()
    resp = (
        sb.table(_CONTACTS_TABLE)
        .select("*")
        .eq("campaign_id", campaign_id)
        .eq("status", "pending")
        .limit(limit)
        .execute()
    )
    return resp.data or []


def _update_campaign_status(campaign_id: str, status: str) -> None:
    sb = get_supabase()
    sb.table(_CAMP_TABLE).update({"status": status, "updated_at": _now()}).eq("id", campaign_id).execute()


def _create_session(campaign_id: str, execution_type: str, contact: dict, prompt_text: str) -> str:
    session_id = str(uuid.uuid4())
    sb = get_supabase()
    sb.table(_EXEC_TABLE).insert({
        "id": session_id,
        "campaign_id": campaign_id,
        "execution_type": execution_type,
        "language": contact.get("language", "en"),
        "status": "active",
        "is_simulation": execution_type == "BROWSER_VOICE",
        "prompt_text": prompt_text,
        "telegram_chat_id": contact.get("telegram_chat_id"),
        "created_at": _now(),
        "updated_at": _now(),
    }).execute()
    return session_id


# ── Channel 1: TELEPHONY (Exotel / Twilio / Mock) ─────────────────────────────

async def _run_telephony(campaign: dict, contacts: list[dict]) -> dict:
    campaign_id = campaign["id"]
    campaign_name = campaign.get("name", "Campaign")
    language = campaign.get("language", "en")

    # Step 1: Pre-generate ElevenLabs audio for all script segments
    log.info("campaign_engine_telephony_audio_prep", campaign_id=campaign_id)
    from app.services.tts_service import generate_campaign_audio
    audio_urls = await generate_campaign_audio(
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        language=language,
        custom_scripts=(campaign.get("script") or campaign.get("template_script")
                        if isinstance(campaign.get("script") or campaign.get("template_script"), dict)
                        else None),
    )
    # Save audio URLs to campaign
    sb = get_supabase()
    sb.table(_CAMP_TABLE).update({"audio_urls": audio_urls}).eq("id", campaign_id).execute()

    # Step 2: Place calls
    provider = get_provider()
    provider_name = active_provider_name()
    placed = 0
    failed = 0

    for contact in contacts[:settings.exotel_max_concurrent * 2]:  # Respect concurrency
        phone = contact.get("phone_e164") or contact.get("phone")
        if not phone:
            continue
        try:
            from app.telephony.providers.base import PlaceCallRequest
            call_id = uuid.uuid4()
            result = await provider.place_call(PlaceCallRequest(
                call_id=call_id,
                to_number=phone,
                caller_id=(
                    settings.twilio_phone_number if provider_name == "twilio"
                    else settings.exotel_caller_id
                ),
                status_callback_url=(
                    f"{settings.webhook_base_url}/webhooks/{settings.webhook_secret}"
                    f"/status?call_id={call_id}"
                ),
                flow_url=(
                    f"{settings.webhook_base_url}/webhooks/{settings.webhook_secret}"
                    f"/flow?call_id={call_id}"
                ),
                custom_field=str(call_id),
            ))
            placed += 1
            log.info("campaign_call_placed", provider=provider_name, phone="[REDACTED]")
        except Exception as exc:
            failed += 1
            log.error("campaign_call_failed", error=str(exc))

    return {
        "channel": "telephony",
        "provider": provider_name,
        "contacts_total": len(contacts),
        "calls_placed": placed,
        "calls_failed": failed,
        "audio_segments_ready": sum(1 for v in audio_urls.values() if v),
    }


# ── Channel 2: BROWSER VOICE (always available) ──────────────────────────────

async def _run_browser(campaign: dict, contacts: list[dict]) -> dict:
    """
    Create a browser voice session for each contact.
    Sessions are available at GET /api/v1/sessions/browser/{id}
    Frontend can drive TTS + response flow for each.
    """
    campaign_id = campaign["id"]
    from app.services.tts_service import build_localized_prompt

    sessions_created = 0
    for contact in contacts:
        try:
            language = contact.get("language") or campaign.get("language", "en")
            prompt = await build_localized_prompt(campaign, language)
            _create_session(campaign_id, "BROWSER_VOICE", contact, prompt)
            sessions_created += 1
        except Exception as exc:
            log.error("browser_session_create_failed", error=str(exc))

    return {
        "channel": "browser",
        "contacts_total": len(contacts),
        "sessions_created": sessions_created,
        "tts_provider": "elevenlabs" if settings.elevenlabs_api_key else "ai_service",
        "note": "Open /api/v1/sessions/browser/{id} to drive each session",
    }


# ── Channel 3: TELEGRAM BOT ───────────────────────────────────────────────────

async def _send_telegram_invite(chat_id: str | int, campaign_name: str, campaign_id: str) -> bool:
    """Send a campaign invitation via Telegram with inline keyboard."""
    if not settings.telegram_bot_token:
        return False
    try:
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Attending", "callback_data": f"campaign:{campaign_id}:confirm"},
                    {"text": "❌ Not attending", "callback_data": f"campaign:{campaign_id}:decline"},
                ],
                [{"text": "📞 Request callback", "callback_data": f"campaign:{campaign_id}:call_later"}],
            ]
        }
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "parse_mode": "HTML",
                    "text": (
                        f"📢 <b>Invitation: {campaign_name}</b>\n\n"
                        "You have been invited to attend. Please select your response:"
                    ),
                    "reply_markup": keyboard,
                },
            )
        return True
    except Exception as exc:
        log.error("telegram_invite_failed", error=str(exc))
        return False


async def _run_telegram(campaign: dict, contacts: list[dict]) -> dict:
    """Send Telegram invitations to contacts that have a telegram_chat_id."""
    campaign_id = campaign["id"]
    campaign_name = campaign.get("name", "Campaign")
    prompt = f"You have been invited to {campaign_name}. Tap a button or send a voice note to respond."

    sent = 0
    skipped = 0

    for contact in contacts:
        chat_id = contact.get("telegram_chat_id")
        if not chat_id:
            skipped += 1
            continue
        try:
            ok = await _send_telegram_invite(chat_id, campaign_name, campaign_id)
            if ok:
                _create_session(campaign_id, "TELEGRAM", contact, prompt)
                sent += 1
        except Exception as exc:
            log.error("telegram_send_failed", error=str(exc))

    return {
        "channel": "telegram",
        "contacts_total": len(contacts),
        "invitations_sent": sent,
        "skipped_no_chat_id": skipped,
    }


# ── Main entry point ──────────────────────────────────────────────────────────

async def run_campaign(
    campaign_id: str,
    channel: Channel = "auto",
    max_contacts: int = 500,
) -> dict:
    """
    Execute a campaign on the specified (or auto-detected) channel.

    Args:
        campaign_id:  UUID of the campaign to run.
        channel:      'auto' | 'telephony' | 'browser' | 'telegram'
        max_contacts: Cap on contacts processed in one run.

    Returns:
        Execution summary dict.
    """
    log.info("campaign_engine_start", campaign_id=campaign_id, requested_channel=channel)

    # Load campaign
    try:
        campaign = _get_campaign(campaign_id)
    except ValueError as exc:
        return {"error": str(exc)}

    if campaign.get("status") not in ("draft", "ready", "scheduled", "paused"):
        return {
            "error": f"Campaign is {campaign.get('status')} — cannot launch",
            "campaign_id": campaign_id,
        }

    # Load contacts
    contacts = _get_contacts(campaign_id, limit=max_contacts)
    if not contacts:
        return {
            "warning": "No pending contacts. Upload a CSV first via POST /api/v1/contacts/import",
            "campaign_id": campaign_id,
        }

    # Resolve channel
    effective_channel = detect_channel() if channel == "auto" else channel
    log.info("campaign_engine_channel", campaign_id=campaign_id, channel=effective_channel)

    # Update status
    _update_campaign_status(campaign_id, "running")

    try:
        if effective_channel == "telephony":
            result = await _run_telephony(campaign, contacts)
        elif effective_channel == "telegram":
            result = await _run_telegram(campaign, contacts)
        else:
            result = await _run_browser(campaign, contacts)

        _update_campaign_status(campaign_id, "running")
        result["campaign_id"] = campaign_id
        result["campaign_name"] = campaign.get("name")
        log.info("campaign_engine_done", **result)
        return result

    except Exception as exc:
        log.error("campaign_engine_error", campaign_id=campaign_id, error=str(exc))
        _update_campaign_status(campaign_id, "paused")
        return {"error": str(exc), "campaign_id": campaign_id}
