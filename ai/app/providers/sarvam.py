"""
Sarvam AI provider — STT (Saaras v4), Translate (Mayura v1), TTS (Bulbul v2).

Key design decisions:
- Uses the official `sarvamai` SDK (sync), called via asyncio executor to avoid blocking.
- The SDK client is a module-level singleton, initialised on first call.
- SARVAM_API_KEY is read exclusively from environment / settings — never logged.
- All provider errors are re-raised as SarvamError (a subclass of RuntimeError)
  with a sanitised message; callers map these to HTTP status codes.
- VAD is NOT used — Sarvam's Saaras handles silence/noise natively.
- Audio is passed through as-is: Sarvam accepts WAV, MP3, AMR, OGG, etc.
  For raw PCM (e.g. Exotel's 8-kHz pcm_s16le) the codec is declared explicitly.

Audio format note (Exotel telephony):
  Exotel recordings are delivered as MP3 or WAV (8 kHz, mono).
  Sarvam's REST API accepts both natively — no resampling needed at this layer.
  If Exotel delivers raw PCM, set input_audio_codec="pcm_s16le" in the request.
"""

from __future__ import annotations

import asyncio
import base64
import io
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

import structlog

log = structlog.get_logger()

# ── Language code translation (ISO-639-1 → BCP-47 Sarvam format) ─────────────
_ISO_TO_BCP47: dict[str, str] = {
    "en": "en-IN",
    "hi": "hi-IN",
    "ml": "ml-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "kn": "kn-IN",
    "bn": "bn-IN",
    "mr": "mr-IN",
    "gu": "gu-IN",
    "od": "od-IN",
    "pa": "pa-IN",
}

_BCP47_TO_ISO: dict[str, str] = {v: k for k, v in _ISO_TO_BCP47.items()}

# TTS voices — one female voice per language, suitable for outbound calling
_CALLING_VOICES: dict[str, str] = {
    # These are short Bulbul v3 speaker IDs. Persona IDs such as
    # ``sanchita_en_customer`` belong to newer model catalogs and return 422
    # when sent with bulbul:v3.
    "en-IN": "shubh",
    "hi-IN": "ritu",
    "ml-IN": "shubh",
    "ta-IN": "priya",
    "te-IN": "kavitha",
    "kn-IN": "shubh",
    "bn-IN": "roopa",
    "mr-IN": "ritu",
    "gu-IN": "pooja",
}


class SarvamError(RuntimeError):
    """Raised for any Sarvam provider failure; message is safe to log."""
    def __init__(self, code: str, message: str, status: int = 500) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


@dataclass
class STTResult:
    transcript: str
    language: str          # ISO-639-1 two-letter code
    language_probability: float
    no_speech: bool
    latency_ms: int
    model: str = "saaras:v4"


@dataclass
class TranslateResult:
    translated_text: str
    model: str = "mayura:v1"


@dataclass
class TTSResult:
    audio_bytes: bytes     # WAV at requested sample rate
    duration_ms: int
    model: str


# ── Singleton client ──────────────────────────────────────────────────────────

_client = None


def _get_client():
    """Return a cached SarvamAI client. Raises SarvamError if key not set."""
    global _client
    if _client is not None:
        return _client

    from app.config import settings
    if not settings.sarvam_api_key:
        raise SarvamError(
            "missing_credentials",
            "SARVAM_API_KEY is not configured",
            status=503,
        )

    try:
        from sarvamai import SarvamAI
        _client = SarvamAI(api_subscription_key=settings.sarvam_api_key)
        log.info("sarvam_client_initialised")
    except Exception as exc:
        raise SarvamError("init_failed", f"Failed to init Sarvam client: {exc}") from exc

    return _client


def _to_bcp47(language: str | None) -> str:
    """Map ISO-639-1 code to BCP-47, default unknown for auto-detect."""
    if language is None:
        return "unknown"
    return _ISO_TO_BCP47.get(language, "unknown")


def _from_bcp47(bcp47: str | None) -> str:
    """Map BCP-47 back to ISO-639-1, default 'en'."""
    if not bcp47:
        return "en"
    return _BCP47_TO_ISO.get(bcp47, bcp47[:2])


@lru_cache(maxsize=1)
def _stt_modes() -> dict[str, str]:
    """Read optional Saaras output modes without exposing credentials."""
    try:
        import yaml
        path = Path(__file__).resolve().parents[2] / "models.yaml"
        config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return config.get("stt_mode", {}) or {}
    except Exception as exc:
        log.warning("stt_mode_config_unavailable", error=str(exc))
        return {}


def _stt_mode_for(language: str | None) -> str | None:
    mode = _stt_modes().get(language or "")
    return mode if mode in ("translit", "codemix") else None


# ── STT ───────────────────────────────────────────────────────────────────────

def _stt_sync(
    audio_bytes: bytes,
    filename: str,
    language_code: str,
    input_audio_codec: str | None,
    keyterms: list[str],
    mode: str | None,
) -> STTResult:
    """Synchronous Sarvam STT call — run in executor."""
    client = _get_client()

    # Wrap bytes in a file-like object with a name (SDK reads .name attribute)
    buf = io.BytesIO(audio_bytes)
    buf.name = filename

    kwargs: dict = {
        "file": buf,
        "model": "saaras:v4",
        "language_code": language_code,
        "with_timestamps": False,
    }
    if input_audio_codec:
        kwargs["input_audio_codec"] = input_audio_codec
    if keyterms:
        kwargs["keyterms"] = keyterms
    if mode:
        kwargs["mode"] = mode

    try:
        t0 = time.monotonic()
        resp = client.speech_to_text.transcribe(**kwargs)
        latency_ms = int((time.monotonic() - t0) * 1000)
    except Exception as exc:
        _handle_sarvam_exception(exc, "stt")

    transcript: str = resp.transcript or ""
    lang_code: str = resp.language_code or language_code
    lang_prob: float = float(getattr(resp, "language_probability", 1.0) or 1.0)

    # Sarvam returns empty transcript for silence; treat as no_speech
    no_speech = not transcript.strip()

    return STTResult(
        transcript=transcript,
        language=_from_bcp47(lang_code),
        language_probability=lang_prob,
        no_speech=no_speech,
        latency_ms=latency_ms,
    )


async def transcribe(
    audio_bytes: bytes,
    filename: str = "audio.wav",
    language: str | None = None,
    input_audio_codec: str | None = None,
    keyterms: list[str] | None = None,
) -> STTResult:
    """
    Async STT via Sarvam Saaras v4.

    Args:
        audio_bytes:       Raw audio bytes (WAV, MP3, AMR, OGG, etc.)
        filename:          Hint for content-type detection (e.g. "call.wav")
        language:          ISO-639-1 code or None for auto-detect
        input_audio_codec: Required for raw PCM (e.g. "pcm_s16le" for Exotel raw)
        keyterms:          Up to 50 domain terms to bias recognition

    Raises:
        SarvamError on all provider failures
    """
    language_code = _to_bcp47(language)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        _stt_sync,
        audio_bytes,
        filename,
        language_code,
        input_audio_codec,
        keyterms or [],
        _stt_mode_for(language),
    )


# ── Translate ─────────────────────────────────────────────────────────────────

def _translate_sync(
    text: str,
    source_language_code: str,
    target_language_code: str,
) -> TranslateResult:
    """Synchronous Sarvam translate call."""
    client = _get_client()
    try:
        t0 = time.monotonic()
        resp = client.text.translate(
            input=text,
            source_language_code=source_language_code,
            target_language_code=target_language_code,
            model="mayura:v1",
            mode="formal",
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
    except Exception as exc:
        _handle_sarvam_exception(exc, "translate")

    return TranslateResult(translated_text=resp.translated_text or text)


async def translate_text(
    text: str,
    source_language: str,
    target_language: str,
) -> TranslateResult:
    """
    Async single-string translation via Sarvam Mayura v1.
    For multi-segment translation, call this per segment (caching is upstream).
    """
    src = _to_bcp47(source_language)
    tgt = _to_bcp47(target_language)
    if src == "unknown":
        src = "en-IN"

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _translate_sync, text, src, tgt)


# ── TTS ───────────────────────────────────────────────────────────────────────

def _tts_sync(
    text: str,
    language_code: str,
    speaker: str,
    speech_sample_rate: int,
    model: str,
) -> TTSResult:
    """Synchronous Sarvam TTS call — run in executor."""
    client = _get_client()
    try:
        t0 = time.monotonic()
        resp = client.text_to_speech.convert(
            text=text,
            language_code=language_code,
            speaker=speaker,
            model=model,
            speech_sample_rate=speech_sample_rate,
            output_audio_codec="wav",
            enable_preprocessing=True,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
    except Exception as exc:
        _handle_sarvam_exception(exc, "tts")

    # SDK returns base64-encoded audio in audios[0]
    try:
        audio_b64: str = resp.audios[0]
        audio_bytes = base64.b64decode(audio_b64)
    except Exception as exc:
        raise SarvamError("tts_decode_failed", f"Could not decode TTS audio: {exc}")

    # Estimate duration from byte count: 16-bit mono PCM
    # duration = bytes / (sample_rate * 2)
    duration_ms = int(len(audio_bytes) / (speech_sample_rate * 2) * 1000)

    return TTSResult(
        audio_bytes=audio_bytes,
        duration_ms=max(duration_ms, 100),
        model=f"sarvam/{model}/{speaker}",
    )


async def synthesize(
    text: str,
    language: str,
    voice: str | None = None,
    speech_sample_rate: int = 8000,
    model: str = "bulbul:v2",
) -> TTSResult:
    """
    Async TTS via Sarvam Bulbul v2.

    Returns TTSResult with raw WAV bytes at speech_sample_rate (default 8 kHz for Exotel).
    """
    bcp47 = _to_bcp47(language)
    if bcp47 == "unknown":
        bcp47 = "en-IN"

    selected_voice = voice or _CALLING_VOICES.get(bcp47, "anushka")

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        _tts_sync,
        text,
        bcp47,
        selected_voice,
        speech_sample_rate,
        model,
    )


# ── Health check ──────────────────────────────────────────────────────────────

def is_configured() -> bool:
    """Return True if SARVAM_API_KEY is set and client can be initialised."""
    try:
        _get_client()
        return True
    except SarvamError:
        return False


# ── Error handler ─────────────────────────────────────────────────────────────

def _handle_sarvam_exception(exc: Exception, op: str) -> None:
    """
    Map Sarvam SDK / HTTP errors to SarvamError.
    Never logs the audio content or API key — only error codes and op name.
    Always raises; return type is NoReturn but not annotated to avoid import.
    """
    msg = str(exc)

    # Rate limit
    if "429" in msg or "rate_limit" in msg.lower() or "quota" in msg.lower():
        log.warning("sarvam_rate_limit", op=op)
        raise SarvamError("rate_limit_exceeded", "Sarvam rate limit exceeded", status=429)

    # Auth / key
    if "403" in msg or "401" in msg or "api_key" in msg.lower() or "authentication" in msg.lower():
        log.error("sarvam_auth_error", op=op)
        raise SarvamError("invalid_api_key", "Sarvam API key is invalid or unauthorised", status=401)

    # Timeout
    if "timeout" in msg.lower() or "timed out" in msg.lower():
        log.warning("sarvam_timeout", op=op)
        raise SarvamError("provider_timeout", "Sarvam request timed out", status=504)

    # Bad audio / request
    if "400" in msg or "422" in msg or "invalid" in msg.lower():
        log.warning("sarvam_bad_request", op=op)
        raise SarvamError("bad_audio", f"Sarvam rejected the {op} request: invalid input", status=422)

    # Server error
    log.error("sarvam_provider_error", op=op, error_type=type(exc).__name__)
    raise SarvamError("provider_error", f"Sarvam {op} failed", status=502)
