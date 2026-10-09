"""
ElevenLabs provider — TTS only.
Uses the official ElevenLabs REST API.

Activated only when ELEVENLABS_API_KEY is set.
Falls back gracefully (raises ElevenLabsUnavailable) when unconfigured.
Never logs the API key.
"""
from __future__ import annotations

import asyncio
from typing import Optional

import httpx
import structlog

from app.core.config import settings

log = structlog.get_logger()

_BASE = "https://api.elevenlabs.io/v1"
_TIMEOUT = httpx.Timeout(30.0)


class ElevenLabsUnavailable(RuntimeError):
    """Raised when ElevenLabs is not configured or the API key is absent."""


def _headers() -> dict[str, str]:
    if not settings.elevenlabs_api_key:
        raise ElevenLabsUnavailable(
            "ELEVENLABS_API_KEY is not set. "
            "Configure it to enable ElevenLabs TTS."
        )
    return {
        "xi-api-key": settings.elevenlabs_api_key,
        "Content-Type": "application/json",
    }


async def tts(
    text: str,
    language: str = "en",
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None,
) -> bytes:
    """
    Convert text to speech using ElevenLabs.

    Args:
        text:      The text to synthesise.
        language:  ISO-639-1 language code (e.g. 'hi', 'ml', 'en').
        voice_id:  Override the default voice. Uses ELEVENLABS_VOICE_ID if not set.
        model_id:  Override the model. Uses ELEVENLABS_MODEL_ID if not set.

    Returns:
        Raw MP3 bytes.

    Raises:
        ElevenLabsUnavailable: if not configured.
        httpx.HTTPStatusError: on API errors.
    """
    v_id = voice_id or settings.elevenlabs_voice_id
    m_id = model_id or settings.elevenlabs_model_id

    body = {
        "text": text,
        "model_id": m_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }

    def _sync_tts() -> bytes:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(
                f"{_BASE}/text-to-speech/{v_id}",
                headers=_headers(),
                json=body,
            )
            resp.raise_for_status()
            return resp.content

    try:
        audio = await asyncio.get_event_loop().run_in_executor(None, _sync_tts)
        log.info("elevenlabs_tts_ok", chars=len(text), voice=v_id, lang=language)
        return audio
    except ElevenLabsUnavailable:
        raise
    except Exception as exc:
        log.error("elevenlabs_tts_error", error=str(exc))
        raise


async def list_voices() -> list[dict]:
    """Return available voices from the ElevenLabs API."""
    def _sync() -> list[dict]:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(f"{_BASE}/voices", headers=_headers())
            resp.raise_for_status()
            return resp.json().get("voices", [])

    return await asyncio.get_event_loop().run_in_executor(None, _sync)


def is_available() -> bool:
    """Return True if ElevenLabs is configured."""
    return bool(settings.elevenlabs_api_key)
