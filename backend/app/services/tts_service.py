"""
Campaign audio pre-generation service.

When a campaign is prepared:
1. Build each script segment (greeting, prompt, reprompt, ack_*, goodbye, voicemail)
2. Call ElevenLabs TTS (primary) or AI service TTS (fallback) for each
3. Store the MP3 as a Supabase Storage object OR serve via the /api/v1/audio/{token} endpoint
4. Return a dict of {segment_key: public_url} that gets saved to the campaign row

During live Twilio/Exotel calls, the flow engine's Play(audio_url=...) uses these URLs.
The telephony provider fetches the MP3 and plays it to the callee.

Result: every real phone call hears ElevenLabs voice, NOT the provider's TTS.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time
from pathlib import Path
from typing import Optional

import structlog

from app.core.config import settings
from app.providers import elevenlabs

log = structlog.get_logger()

# In-process audio cache: token -> mp3 bytes
# For production, replace with Supabase Storage uploads
_AUDIO_CACHE: dict[str, bytes] = {}
_TOKEN_TTL = 24 * 3600   # 24 hours


def _make_token(segment_key: str, campaign_id: str) -> str:
    """Generate a signed token to serve audio from the backend."""
    raw = f"{campaign_id}:{segment_key}:{int(time.time() // _TOKEN_TTL)}"
    sig = hmac.new(
        settings.webhook_secret.encode(),
        raw.encode(),
        hashlib.sha256,
    ).hexdigest()[:16]
    payload = base64.urlsafe_b64encode(f"{raw}:{sig}".encode()).decode().rstrip("=")
    return payload


def _audio_url(token: str) -> str:
    """Public URL that Twilio/Exotel can fetch during a live call."""
    return f"{settings.webhook_base_url}/api/v1/audio/{token}"


# Default script templates per segment
_SEGMENT_SCRIPTS: dict[str, str] = {
    "greeting": (
        "Hello! You have been invited to {event_name}. "
        "This is an automated call from {org_name}. "
        "Please press 1 to confirm your attendance, "
        "press 2 if you cannot attend, "
        "or press 3 to request a callback."
    ),
    "prompt": (
        "Press 1 to confirm, 2 to decline, or 3 for a callback."
    ),
    "reprompt": (
        "We did not hear your response. "
        "Please press 1 to confirm, 2 to decline, or 3 for a callback."
    ),
    "ack_confirm": (
        "Thank you for confirming! We look forward to seeing you at {event_name}. Goodbye!"
    ),
    "ack_decline": (
        "We understand. Thank you for letting us know. Goodbye!"
    ),
    "ack_reschedule": (
        "Noted! We will follow up with updated timing. Goodbye!"
    ),
    "ack_call_later": (
        "Of course. Someone will call you back shortly. Goodbye!"
    ),
    "ack_stop": (
        "You have been removed from our calling list. You will not receive further calls. Goodbye!"
    ),
    "ack_unclear": (
        "We could not process your response. We will follow up. Goodbye!"
    ),
    "goodbye": (
        "Thank you for your time. Goodbye!"
    ),
    "voicemail": (
        "Hello! This is a message for {event_name} from {org_name}. "
        "Please call us back or visit our website to confirm your attendance. Thank you!"
    ),
}


async def localize_text(text: str, language: str, source_language: str = "en") -> str:
    """Translate campaign text before synthesis for the contact's language."""
    target = language.lower().split("-")[0]
    if not text or target == source_language.lower().split("-")[0]:
        return text
    from app.ai_client.client import get_ai_client
    result = await get_ai_client().translate(
        {"text": text}, source_lang=source_language, target_lang=target
    )
    return result.segments.get("text", text)


async def build_localized_prompt(campaign: dict, language: str) -> str:
    """Build the spoken invitation from template script or campaign brief."""
    script = campaign.get("script") or campaign.get("template_script")
    if isinstance(script, dict):
        text = script.get("greeting") or script.get("prompt") or next(iter(script.values()), "")
    else:
        text = str(script or campaign.get("brief") or "")
    if not text:
        text = (
            f"Hello! You have been invited to {campaign.get('name', 'this event')}. "
            "Please press 1 to confirm, 2 to decline, or 3 to request a callback."
        )
    text = text.replace("{event_name}", str(campaign.get("name", "this event")))
    text = text.replace("{org_name}", settings.org_name)
    return await localize_text(text, language)


async def synthesize_text(text: str, language: str, voice_id: Optional[str] = None) -> tuple[bytes, str]:
    """Synthesize text using the configured provider and return audio plus provider name."""
    language = language.lower().split("-")[0]
    provider = settings.tts_provider.lower()
    if provider in {"auto", "elevenlabs"} and elevenlabs.is_available():
        try:
            return await elevenlabs.tts(text=text, language=language, voice_id=voice_id), "elevenlabs"
        except Exception:
            if provider == "elevenlabs":
                raise
            log.warning("elevenlabs_failed_using_sarvam")
    if provider == "elevenlabs":
        raise RuntimeError("TTS_PROVIDER=elevenlabs but ELEVENLABS_API_KEY is not configured")
    from app.ai_client.client import get_ai_client
    return await get_ai_client().tts(text=text, language=language, voice=voice_id), "sarvam"


async def generate_campaign_audio(
    campaign_id: str,
    campaign_name: str,
    language: str = "en",
    voice_id: Optional[str] = None,
    custom_scripts: Optional[dict[str, str]] = None,
) -> dict[str, str]:
    """
    Generate all audio segments for a campaign using ElevenLabs TTS.

    Args:
        campaign_id:     Campaign UUID
        campaign_name:   Used in script text substitution
        language:        ISO-639-1 code (for TTS voice selection)
        voice_id:        Override ElevenLabs voice. Uses default if None.
        custom_scripts:  Override any default segment script text.

    Returns:
        Dict mapping segment_key → public audio URL.
        All URLs are served via the /api/v1/audio/{token} backend endpoint.

    Falls back to AI service TTS if ElevenLabs is unavailable.
    Falls back to empty string (silent) if both fail — call flow handles missing audio gracefully.
    """
    scripts = dict(_SEGMENT_SCRIPTS)
    if custom_scripts:
        scripts.update(custom_scripts)

    # Substitute variables
    substitutions = {
        "event_name": campaign_name,
        "org_name": settings.org_name,
    }
    scripts = {
        k: v.format_map(substitutions) for k, v in scripts.items()
    }

    if language.lower().split("-")[0] != "en":
        translated: dict[str, str] = {}
        for key, value in scripts.items():
            try:
                translated[key] = await localize_text(value, language)
            except Exception as exc:
                log.warning("campaign_script_translation_failed", segment=key, error=str(exc))
                translated[key] = value
        scripts = translated

    audio_urls: dict[str, str] = {}
    tts_provider = settings.tts_provider.lower()

    last_error: str | None = None

    for segment_key, text in scripts.items():
        try:
            audio_bytes, tts_provider = await synthesize_text(
                text=text, language=language, voice_id=voice_id
            )

            # Store in cache and generate a servable URL
            token = _make_token(segment_key, campaign_id)
            _AUDIO_CACHE[token] = audio_bytes

            audio_urls[segment_key] = _audio_url(token)
            log.info(
                "campaign_audio_generated",
                campaign_id=campaign_id,
                segment=segment_key,
                provider=tts_provider,
                bytes=len(audio_bytes),
            )

        except Exception as exc:
            last_error = str(exc)
            log.error(
                "campaign_audio_generation_failed",
                campaign_id=campaign_id,
                segment=segment_key,
                error=last_error,
            )
            audio_urls[segment_key] = ""   # flow engine handles empty URLs gracefully

    # If every segment failed, surface the error so the caller knows what went wrong
    if last_error and not any(v for v in audio_urls.values()):
        raise RuntimeError(f"TTS failed for all segments ({tts_provider}): {last_error}")

    return audio_urls


def get_cached_audio(token: str) -> Optional[bytes]:
    """Retrieve cached audio bytes by token. Returns None if expired/missing."""
    return _AUDIO_CACHE.get(token)


def clear_campaign_audio(campaign_id: str) -> None:
    """Remove all cached audio for a campaign (e.g. on cancel)."""
    to_remove = [k for k in _AUDIO_CACHE if campaign_id in k]
    for k in to_remove:
        del _AUDIO_CACHE[k]
