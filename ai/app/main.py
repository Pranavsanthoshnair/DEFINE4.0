"""
Veylo AI Service — FastAPI application.
Port 8200, internal network only.
Auth: X-Internal-Token header on all routes.

Provider: Sarvam AI (Saaras v4 STT, Mayura v1 translate, Bulbul v2 TTS).
Stub mode: AI_STUB=true returns deterministic fake responses for dev/CI.
"""

from __future__ import annotations

import json
import math
import struct
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.config import settings
from app.dependencies import require_token
from app.schemas import (
    HealthResponse,
    IntentRequest,
    IntentResponse,
    ModelStatus,
    SpeechIntentResponse,
    STTResponse,
    TranslateRequest,
    TranslateResponse,
    TTSRequest,
)

log = structlog.get_logger()

# ── Service state ─────────────────────────────────────────────────────────────
_model_status: dict[str, ModelStatus] = {
    "stt": "stub",
    "intent": "stub",
    "translate": "stub",
    "tts": "stub",
}


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _model_status

    log.info("ai_service_starting", stub=settings.ai_stub, port=settings.port)

    if settings.ai_stub:
        log.info("ai_service_stub_mode_active")
    else:
        # Probe Sarvam connectivity on startup — warm the singleton client
        from app.providers.sarvam import is_configured, SarvamError
        if is_configured():
            _model_status = {
                "stt": "loaded",
                "intent": "loaded",    # intent uses rules + LLM, not a local model
                "translate": "loaded",
                "tts": "loaded",
            }
            log.info("sarvam_provider_ready")
        else:
            _model_status = {
                "stt": "unavailable",
                "intent": "loaded",   # rules-only intent still works
                "translate": "unavailable",
                "tts": "unavailable",
            }
            log.warning("sarvam_api_key_missing_or_invalid")

    log.info("ai_service_ready", model_status=_model_status)
    yield
    log.info("ai_service_shutdown")


# ── App factory ────────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="Veylo AI Service",
        description=(
            "STT (Sarvam Saaras v4), intent classification, "
            "translation (Sarvam Mayura v1), and TTS (Sarvam Bulbul v2) "
            "for Veylo calling campaigns."
        ),
        version="0.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── /healthz — public, no auth ─────────────────────────────────────────────
    @app.get("/healthz", response_model=HealthResponse, tags=["health"])
    async def healthz() -> HealthResponse:
        all_ok = all(s in ("loaded", "stub") for s in _model_status.values())
        return HealthResponse(
            status="ok" if all_ok else "degraded",
            models=_model_status,  # type: ignore[arg-type]
        )

    # ── /v1/stt ───────────────────────────────────────────────────────────────
    @app.post("/v1/stt", response_model=STTResponse, tags=["stt"])
    async def stt(
        audio: UploadFile = File(...),
        language: str | None = Form(default=None),
        _: None = Depends(require_token),
    ) -> STTResponse:
        data = await audio.read()

        if len(data) > 5 * 1024 * 1024:
            raise HTTPException(
                413,
                detail={"error": {"code": "audio_too_large", "message": "Audio exceeds 5 MB"}},
            )
        if language and language not in _supported_langs():
            raise HTTPException(
                400,
                detail={"error": {"code": "unsupported_language",
                                  "message": f"'{language}' is not supported"}},
            )

        if settings.ai_stub:
            return _stub_stt(audio.filename or "", language)

        return await _live_stt(data, audio.filename or "audio.wav", language)

    # ── /v1/intent ────────────────────────────────────────────────────────────
    @app.post("/v1/intent", response_model=IntentResponse, tags=["intent"])
    async def intent(
        body: IntentRequest,
        _: None = Depends(require_token),
    ) -> IntentResponse:
        if body.language not in _supported_langs():
            raise HTTPException(
                400,
                detail={"error": {"code": "unsupported_language",
                                  "message": f"'{body.language}' is not supported"}},
            )

        if settings.ai_stub:
            return _stub_intent(body.text)

        from app.intent.pipeline import run_pipeline
        label, conf, source, latency_ms = await run_pipeline(
            body.text, body.language, body.allowed_intents
        )
        return IntentResponse(
            intent=label, confidence=conf, source=source, latency_ms=latency_ms
        )

    # ── /v1/speech-intent ─────────────────────────────────────────────────────
    @app.post("/v1/speech-intent", response_model=SpeechIntentResponse, tags=["stt"])
    async def speech_intent(
        audio: UploadFile = File(...),
        language: str | None = Form(default=None),
        allowed_intents: str | None = Form(default=None),
        _: None = Depends(require_token),
    ) -> SpeechIntentResponse:
        data = await audio.read()

        if len(data) > 5 * 1024 * 1024:
            raise HTTPException(
                413,
                detail={"error": {"code": "audio_too_large", "message": "Audio exceeds 5 MB"}},
            )

        parsed_intents = json.loads(allowed_intents) if allowed_intents else None

        if settings.ai_stub:
            return _stub_speech_intent(audio.filename or "", language)

        t0 = time.monotonic()

        stt_result = await _live_stt(data, audio.filename or "audio.wav", language)

        if stt_result.no_speech:
            return SpeechIntentResponse(
                text="", language=stt_result.language,
                intent="unclear", confidence=0.0, source="rules",
                stt_model=stt_result.model,
                latency_ms=int((time.monotonic() - t0) * 1000),
                no_speech=True,
            )

        from app.intent.pipeline import run_pipeline
        label, conf, source, _ = await run_pipeline(
            stt_result.text, stt_result.language, parsed_intents
        )

        return SpeechIntentResponse(
            text=stt_result.text, language=stt_result.language,
            intent=label, confidence=conf, source=source,
            stt_model=stt_result.model,
            latency_ms=int((time.monotonic() - t0) * 1000),
            no_speech=False, truncated=stt_result.truncated,
        )

    # ── /v1/translate ─────────────────────────────────────────────────────────
    @app.post("/v1/translate", response_model=TranslateResponse, tags=["translate"])
    async def translate(
        body: TranslateRequest,
        _: None = Depends(require_token),
    ) -> TranslateResponse:
        if len(body.segments) > 20:
            raise HTTPException(
                400,
                detail={"error": {"code": "too_many_segments",
                                  "message": "Max 20 segments per call"}},
            )
        if body.target_language not in _supported_langs():
            raise HTTPException(
                400,
                detail={"error": {"code": "unsupported_language",
                                  "message": f"'{body.target_language}' is not supported"}},
            )

        if settings.ai_stub:
            translated = {
                k: f"[{body.target_language}] {v}"
                for k, v in body.segments.items()
            }
            return TranslateResponse(segments=translated, model="stub")

        return await _live_translate(body)

    # ── /v1/tts ───────────────────────────────────────────────────────────────
    @app.post("/v1/tts", tags=["tts"])
    async def tts(
        body: TTSRequest,
        _: None = Depends(require_token),
    ) -> Response:
        if body.language not in _supported_langs():
            raise HTTPException(
                400,
                detail={"error": {"code": "unsupported_language",
                                  "message": f"'{body.language}' is not supported"}},
            )
        if len(body.text) > 2000:
            raise HTTPException(
                400,
                detail={"error": {"code": "text_too_long",
                                  "message": "Max 2000 characters"}},
            )

        if settings.ai_stub:
            wav = _make_sine_wav(1.0)
            return Response(
                content=wav, media_type="audio/wav",
                headers={"X-Duration-Ms": "1000", "X-Tts-Model": "stub"},
            )

        return await _live_tts(body)

    return app


# ── Live provider calls ────────────────────────────────────────────────────────

async def _live_stt(
    data: bytes,
    filename: str,
    language: str | None,
) -> STTResponse:
    """Route STT call based on settings.stt_provider."""
    provider = settings.stt_provider.lower()

    if provider == "groq":
        return await _groq_stt(data, filename, language)
    elif provider == "sarvam":
        return await _sarvam_stt(data, filename, language)
    else:
        # auto: race both, return first, fallback if one errors
        return await _auto_stt(data, filename, language)


async def _auto_stt(
    data: bytes,
    filename: str,
    language: str | None,
) -> STTResponse:
    """
    Race Sarvam and Groq concurrently. Return the first result.
    If one provider fails, return the other's result.
    If both fail, raise the Sarvam error (primary).
    """
    import asyncio as _asyncio

    sarvam_task = _asyncio.ensure_future(_sarvam_stt(data, filename, language))
    groq_task   = _asyncio.ensure_future(_groq_stt(data, filename, language))

    done, pending = await _asyncio.wait(
        [sarvam_task, groq_task],
        return_when=_asyncio.FIRST_COMPLETED,
    )

    winner = done.pop()
    # Cancel the slower task
    for t in pending:
        t.cancel()

    try:
        result = winner.result()
        return result
    except Exception:
        # Winner failed — wait for the other one
        for t in pending:
            try:
                return await t
            except Exception:
                pass
        # Both failed — re-raise from winner
        winner.result()  # raises


async def _sarvam_stt(
    data: bytes,
    filename: str,
    language: str | None,
) -> STTResponse:
    """Call Sarvam STT; map SarvamError to HTTPException."""
    from app.providers.sarvam import transcribe, SarvamError

    codec: str | None = None
    if settings.exotel_audio_codec not in ("auto", ""):
        codec = settings.exotel_audio_codec

    try:
        result = await transcribe(
            audio_bytes=data,
            filename=filename,
            language=language,
            input_audio_codec=codec,
        )
    except SarvamError as exc:
        _raise_provider_error(exc)

    return STTResponse(
        text=result.transcript,
        language=result.language,
        confidence=0.0 if result.no_speech else round(result.language_probability, 3),
        duration_ms=0,
        latency_ms=result.latency_ms,
        model=result.model,
        no_speech=result.no_speech,
    )


async def _groq_stt(
    data: bytes,
    filename: str,
    language: str | None,
) -> STTResponse:
    """Call Groq Whisper STT; map GroqSTTError to HTTPException."""
    from app.providers.groq_whisper import transcribe as groq_transcribe, GroqSTTError

    try:
        result = await groq_transcribe(
            audio_bytes=data,
            filename=filename,
            language=language,
        )
    except GroqSTTError as exc:
        _raise_provider_error(exc)

    return STTResponse(
        text=result.transcript,
        language=result.language,
        confidence=0.0 if result.no_speech else 0.95,
        duration_ms=0,
        latency_ms=result.latency_ms,
        model=result.model,
        no_speech=result.no_speech,
    )


async def _live_translate(body: TranslateRequest) -> TranslateResponse:
    """Translate all segments via Sarvam, preserving placeholders."""
    from app.providers.sarvam import translate_text, SarvamError
    from app.translate.placeholders import protect_segments, restore_segments, validate_segments
    import asyncio

    protected, mappings = protect_segments(body.segments)

    # Translate all segments concurrently
    async def translate_one(key: str, text: str) -> tuple[str, str]:
        try:
            r = await translate_text(text, body.source_language, body.target_language)
            return key, r.translated_text
        except SarvamError as exc:
            _raise_provider_error(exc)

    tasks = [translate_one(k, v) for k, v in protected.items()]
    pairs = await asyncio.gather(*tasks)
    translated_protected = dict(pairs)

    errors = validate_segments(protected, translated_protected, mappings)
    if errors:
        raise HTTPException(
            422,
            detail={"error": {
                "code": "placeholder_lost",
                "message": "Placeholder(s) lost in translation",
                "details": errors,
            }},
        )

    final = restore_segments(translated_protected, mappings)
    return TranslateResponse(segments=final, model="sarvam/mayura:v1")


async def _live_tts(body: TTSRequest) -> Response:
    """Synthesise via Sarvam Bulbul v2."""
    from app.providers.sarvam import synthesize, SarvamError

    try:
        result = await synthesize(
            text=body.text,
            language=body.language,
            voice=body.voice,
            speech_sample_rate=settings.sarvam_tts_sample_rate,
            model=settings.sarvam_tts_model,
        )
    except SarvamError as exc:
        _raise_provider_error(exc)

    return Response(
        content=result.audio_bytes,
        media_type="audio/wav",
        headers={
            "X-Duration-Ms": str(result.duration_ms),
            "X-Tts-Model": result.model,
        },
    )


def _raise_provider_error(exc) -> None:
    """Map SarvamError to HTTPException. Always raises."""
    _STATUS_TO_HTTP = {
        401: 502,   # our upstream key error → report as 502 (server-side config problem)
        422: 422,   # bad input
        429: 429,   # rate limit — caller can retry
        504: 504,   # timeout
        502: 502,   # generic provider failure
        503: 503,   # not configured
    }
    http_status = _STATUS_TO_HTTP.get(exc.status, 502)
    raise HTTPException(
        http_status,
        detail={"error": {"code": exc.code, "message": str(exc)}},
    )


# ── Stub helpers ───────────────────────────────────────────────────────────────

def _make_sine_wav(duration_sec: float = 1.0, freq: int = 440) -> bytes:
    """Generate a 1-second 8 kHz mono PCM16 sine wave WAV."""
    sample_rate = 8000
    n_samples = int(sample_rate * duration_sec)
    samples = [
        int(32767 * math.sin(2 * math.pi * freq * i / sample_rate))
        for i in range(n_samples)
    ]
    data = struct.pack(f"<{n_samples}h", *samples)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + len(data), b"WAVE",
        b"fmt ", 16, 1, 1,
        sample_rate, sample_rate * 2, 2, 16,
        b"data", len(data),
    )
    return header + data


def _stub_stt(filename: str, language: str | None) -> STTResponse:
    fname = filename.lower()
    if "noise" in fname or "silence" in fname:
        text, no_speech = "", True
    elif "no" in fname or "decline" in fname:
        text, no_speech = "no I will not come", False
    elif "later" in fname or "busy" in fname:
        text, no_speech = "call me later I am busy", False
    elif "stop" in fname:
        text, no_speech = "please stop calling", False
    else:
        text, no_speech = "yes I will come", False

    return STTResponse(
        text=text,
        language=language or "en",
        confidence=0.0 if no_speech else 0.92,
        duration_ms=1000,
        latency_ms=5,
        model="stub/saaras:v4",
        no_speech=no_speech,
    )


def _stub_intent(text: str) -> IntentResponse:
    t = text.lower()
    if not t:
        intent, conf = "unclear", 0.0
    elif any(w in t for w in ("stop", "don't call", "remove", "opt out")):
        intent, conf = "stop_calling", 0.95
    elif any(w in t for w in ("later", "busy", "baad", "pinne", "call back")):
        intent, conf = "call_later", 0.90
    elif any(w in t for w in ("reschedule", "another time", "change")):
        intent, conf = "reschedule", 0.90
    elif any(w in t for w in ("no", "not", "nahi", "illa", "illai", "decline")):
        intent, conf = "decline", 0.90
    else:
        intent, conf = "confirm", 0.90

    return IntentResponse(  # type: ignore[call-arg]
        intent=intent, confidence=conf, source="rules", latency_ms=1
    )


def _stub_speech_intent(filename: str, language: str | None) -> SpeechIntentResponse:
    stt = _stub_stt(filename, language)
    if stt.no_speech:
        return SpeechIntentResponse(
            text="", language=stt.language,
            intent="unclear", confidence=0.0, source="rules",
            stt_model=stt.model, latency_ms=stt.latency_ms, no_speech=True,
        )
    intent_r = _stub_intent(stt.text)
    return SpeechIntentResponse(
        text=stt.text, language=stt.language,
        intent=intent_r.intent, confidence=intent_r.confidence,
        source=intent_r.source, stt_model=stt.model,
        latency_ms=stt.latency_ms + intent_r.latency_ms,
        no_speech=False,
    )


def _supported_langs() -> set[str]:
    return {"en", "hi", "ml", "ta", "te", "kn", "bn", "mr", "gu"}


# ── Entry point ────────────────────────────────────────────────────────────────
app = create_app()
