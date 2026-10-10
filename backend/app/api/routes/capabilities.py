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


@router.get("/capabilities/validate")
async def validate_credentials() -> dict:
    """
    Live credential check — actually pings external providers.
    Call this after setting keys to confirm everything works.
    Returns no secrets — only success/failure flags and safe messages.
    """
    results: dict = {}

    # ── Exotel ───────────────────────────────────────────────────────────────
    provider = settings.call_provider.lower()
    if provider in ("exotel", "auto") and settings.exotel_api_key:
        from app.services.exotel_service import validate_credentials as _validate_exotel
        exotel_result = await _validate_exotel()
        results["exotel"] = exotel_result
    else:
        results["exotel"] = {
            "ok": False,
            "error": "EXOTEL_* keys not set or CALL_PROVIDER != exotel/auto",
        }

    # ── ElevenLabs ───────────────────────────────────────────────────────────
    if settings.elevenlabs_api_key:
        try:
            import httpx as _httpx
            async with _httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(
                    "https://api.elevenlabs.io/v1/user",
                    headers={"xi-api-key": settings.elevenlabs_api_key},
                )
            if resp.status_code == 200:
                user = resp.json()
                results["elevenlabs"] = {
                    "ok": True,
                    "tier": user.get("subscription", {}).get("tier", "unknown"),
                    "character_count": user.get("subscription", {}).get("character_count", 0),
                    "character_limit": user.get("subscription", {}).get("character_limit", 0),
                }
            elif resp.status_code == 401:
                results["elevenlabs"] = {"ok": False, "error": "Invalid ELEVENLABS_API_KEY (401)"}
            else:
                results["elevenlabs"] = {"ok": False, "error": f"HTTP {resp.status_code}"}
        except Exception as exc:
            results["elevenlabs"] = {"ok": False, "error": str(exc)}
    else:
        results["elevenlabs"] = {"ok": False, "error": "ELEVENLABS_API_KEY not set"}

    # ── Summary ───────────────────────────────────────────────────────────────
    all_ok = all(v.get("ok", False) for v in results.values())
    results["summary"] = {
        "ready_for_live_calls": results.get("exotel", {}).get("ok", False),
        "tts_ready": results.get("elevenlabs", {}).get("ok", False),
        "all_ok": all_ok,
    }
    return results

