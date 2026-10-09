"""
Capabilities endpoint — reports which execution channels are configured.
Frontend calls GET /api/v1/capabilities to know what buttons to show.
No credentials are ever returned — only boolean availability flags.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()


class ChannelStatus(BaseModel):
    available: bool
    reason: str          # human-readable, safe to show in UI


class CapabilitiesResponse(BaseModel):
    telephony: ChannelStatus
    browser_voice: ChannelStatus
    telegram: ChannelStatus
    tts: ChannelStatus
    stt: ChannelStatus
    ai_service: ChannelStatus


def _telephony_status() -> ChannelStatus:
    """Resolve which telephony backend is active."""
    provider = settings.call_provider.lower()

    if provider == "exotel" or (provider == "auto" and settings.exotel_api_key):
        if settings.exotel_api_key and settings.exotel_api_token and settings.exotel_sid:
            return ChannelStatus(available=True, reason="Exotel configured")
        return ChannelStatus(available=False, reason="Exotel credentials incomplete")

    if provider == "twilio" or (provider == "auto" and settings.twilio_account_sid):
        if settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_phone_number:
            return ChannelStatus(available=True, reason="Twilio configured")
        return ChannelStatus(available=False, reason="Twilio credentials incomplete")

    if provider == "mock":
        return ChannelStatus(available=True, reason="Mock provider (no real calls)")

    # auto with nothing configured
    return ChannelStatus(available=False, reason="No telephony provider configured")


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities() -> CapabilitiesResponse:
    """
    Returns which execution channels and AI capabilities are available.
    Safe to call unauthenticated — returns no secrets.
    """
    has_elevenlabs = bool(settings.elevenlabs_api_key)
    has_sarvam = bool(getattr(settings, "sarvam_api_key", ""))  # on AI service
    has_groq = bool(settings.groq_api_key)
    has_ai_service = bool(settings.ai_base_url and settings.ai_internal_token)

    tts_available = has_elevenlabs or has_sarvam
    tts_reason = (
        "ElevenLabs" if has_elevenlabs
        else "Sarvam AI" if has_sarvam
        else "No TTS provider configured"
    )

    stt_available = has_sarvam or has_groq or has_ai_service
    stt_reason = (
        "AI service (Sarvam + Groq)" if has_ai_service
        else "Groq Whisper" if has_groq
        else "No STT provider configured"
    )

    return CapabilitiesResponse(
        telephony=_telephony_status(),
        browser_voice=ChannelStatus(
            available=True,
            reason="Always available — browser recording + AI pipeline",
        ),
        telegram=ChannelStatus(
            available=bool(settings.telegram_bot_token),
            reason="Telegram bot configured" if settings.telegram_bot_token
                   else "Set TELEGRAM_BOT_TOKEN to enable",
        ),
        tts=ChannelStatus(available=tts_available, reason=tts_reason),
        stt=ChannelStatus(available=stt_available, reason=stt_reason),
        ai_service=ChannelStatus(
            available=has_ai_service,
            reason="AI service reachable" if has_ai_service else "AI_BASE_URL or AI_INTERNAL_TOKEN not set",
        ),
    )
