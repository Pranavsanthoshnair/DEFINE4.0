"""
Groq Whisper provider — cloud STT via Groq's Whisper Large v3 Turbo.

No local model weights. Groq runs Whisper on their infrastructure.
Free tier: 7,200 audio seconds/day, 2MB max file size per request.

Whisper Large v3 Turbo:
  - Excellent multilingual accuracy (English + Indian languages)
  - ~150 words/second inference speed on Groq
  - Supports: wav, mp3, mp4, mpeg, mpga, m4a, webm, ogg, flac, opus

Comparison vs Sarvam Saaras v4:
  - Sarvam: purpose-built for Indian langs, understands code-mixing
  - Groq Whisper: stronger on English, decent on Indic, lower latency
  - Use the benchmark script (stt_benchmark.py) to compare on your data
"""

from __future__ import annotations

import asyncio
import io
import time
from dataclasses import dataclass

import structlog

log = structlog.get_logger()

# Groq supports up to 2 MB per request on free tier
GROQ_MAX_BYTES = 2 * 1024 * 1024

# Groq language codes (BCP-47 → Groq uses standard ISO-639-1)
_SUPPORTED_LANGS = {
    "en", "hi", "ml", "ta", "te", "kn", "bn", "mr", "gu",
    "pa", "ur", "ne", "si",
}


class GroqSTTError(RuntimeError):
    """Raised for Groq provider failures."""
    def __init__(self, code: str, message: str, status: int = 502) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


@dataclass
class GroqSTTResult:
    transcript: str
    language: str          # ISO-639-1
    no_speech: bool
    latency_ms: int
    model: str = "groq/whisper-large-v3-turbo"


# ── Singleton client ──────────────────────────────────────────────────────────

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client

    from app.config import settings
    if not settings.groq_api_key:
        raise GroqSTTError(
            "missing_credentials",
            "GROQ_API_KEY is not configured",
            status=503,
        )

    try:
        from groq import Groq
        _client = Groq(api_key=settings.groq_api_key)
        log.info("groq_client_initialised")
    except Exception as exc:
        raise GroqSTTError("init_failed", f"Groq init failed: {exc}") from exc

    return _client


# ── STT ───────────────────────────────────────────────────────────────────────

def _stt_sync(
    audio_bytes: bytes,
    filename: str,
    language: str | None,
) -> GroqSTTResult:
    """Synchronous Groq STT — run in executor."""
    if len(audio_bytes) > GROQ_MAX_BYTES:
        raise GroqSTTError(
            "audio_too_large",
            f"Groq free tier max is 2 MB, got {len(audio_bytes)//1024} KB",
            status=413,
        )

    client = _get_client()

    buf = io.BytesIO(audio_bytes)
    buf.name = filename

    kwargs: dict = {
        "file": (filename, buf, "audio/wav"),
        "model": "whisper-large-v3-turbo",
        "response_format": "verbose_json",
    }

    # Only pass language if it's known — Groq auto-detects otherwise
    if language and language in _SUPPORTED_LANGS:
        kwargs["language"] = language

    try:
        t0 = time.monotonic()
        resp = client.audio.transcriptions.create(**kwargs)
        latency_ms = int((time.monotonic() - t0) * 1000)
    except Exception as exc:
        _handle_groq_exception(exc)

    transcript: str = resp.text or ""
    detected_lang: str = getattr(resp, "language", language or "en") or "en"

    # Map verbose language name back to ISO code if needed
    # (Groq returns e.g. "english", "hindi" as full names in verbose_json)
    detected_lang = _normalize_lang(detected_lang)

    return GroqSTTResult(
        transcript=transcript,
        language=detected_lang,
        no_speech=not transcript.strip(),
        latency_ms=latency_ms,
    )


async def transcribe(
    audio_bytes: bytes,
    filename: str = "audio.wav",
    language: str | None = None,
) -> GroqSTTResult:
    """
    Async STT via Groq Whisper Large v3 Turbo.

    Args:
        audio_bytes: Raw audio (WAV, MP3, OGG, etc.) — max 2 MB on free tier
        filename:    Hint for content-type (e.g. "call.wav")
        language:    ISO-639-1 or None for auto-detect

    Raises:
        GroqSTTError on all provider failures
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _stt_sync, audio_bytes, filename, language)


def is_configured() -> bool:
    try:
        _get_client()
        return True
    except GroqSTTError:
        return False


# ── Helpers ───────────────────────────────────────────────────────────────────

_LANG_NAME_TO_ISO = {
    "english": "en", "hindi": "hi", "malayalam": "ml",
    "tamil": "ta", "telugu": "te", "kannada": "kn",
    "bengali": "bn", "marathi": "mr", "gujarati": "gu",
    "punjabi": "pa", "urdu": "ur", "nepali": "ne",
    "sinhala": "si",
}


def _normalize_lang(lang: str) -> str:
    """Convert Groq's verbose language name to ISO-639-1 code."""
    lang = lang.lower().strip()
    if lang in _LANG_NAME_TO_ISO:
        return _LANG_NAME_TO_ISO[lang]
    # Already a 2-letter code
    if len(lang) == 2:
        return lang
    return lang[:2]


def _handle_groq_exception(exc: Exception) -> None:
    msg = str(exc)

    if "429" in msg or "rate_limit" in msg.lower():
        log.warning("groq_rate_limit")
        raise GroqSTTError("rate_limit", "Groq rate limit hit", status=429)

    if "401" in msg or "403" in msg or "api_key" in msg.lower():
        log.error("groq_auth_error")
        raise GroqSTTError("invalid_api_key", "Groq API key is invalid", status=401)

    if "413" in msg or "too large" in msg.lower():
        raise GroqSTTError("audio_too_large", "Audio file too large for Groq", status=413)

    if "timeout" in msg.lower():
        raise GroqSTTError("timeout", "Groq request timed out", status=504)

    if "400" in msg or "invalid" in msg.lower():
        raise GroqSTTError("bad_request", f"Groq rejected request: {msg[:100]}", status=422)

    log.error("groq_provider_error", error_type=type(exc).__name__)
    raise GroqSTTError("provider_error", "Groq STT failed", status=502)
