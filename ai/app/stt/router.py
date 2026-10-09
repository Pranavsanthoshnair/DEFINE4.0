"""
STT router: chooses the right engine per language from models.yaml,
enforces concurrency limits, and exposes the /v1/stt endpoint.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import yaml
import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.config import settings
from app.schemas import STTResponse
from app.stt.base import STTEngine, STTResult
from app.dependencies import require_token

log = structlog.get_logger()
router = APIRouter()

# ── Concurrency gate ──────────────────────────────────────────────────────────
_semaphore: asyncio.Semaphore | None = None


def get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.stt_max_concurrent)
    return _semaphore


# ── Engine registry ──────────────────────────────────────────────────────────
_engines: dict[str, STTEngine] = {}


def register_engine(name: str, engine: STTEngine) -> None:
    _engines[name] = engine


def get_engine_for_language(language: str | None) -> STTEngine:
    """Pick best engine per language mapping from models.yaml; fall back to default."""
    from app.models_registry import engine_for_language  # late import
    return engine_for_language(language, _engines)


# ── Route ────────────────────────────────────────────────────────────────────

@router.post("/v1/stt", response_model=STTResponse)
async def stt(
    audio: UploadFile = File(...),
    language: str | None = Form(default=None),
    _: None = Depends(require_token),
) -> STTResponse:
    """
    Transcribe an 8 kHz or 16 kHz mono WAV file.
    Returns contract-exact STTResponse.
    """
    data = await audio.read()
    if len(data) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio exceeds 2 MB limit")

    if language and language not in _supported_languages():
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "unsupported_language", "message": f"Language '{language}' is not supported"}},
        )

    engine = get_engine_for_language(language)

    sem = get_semaphore()
    try:
        await asyncio.wait_for(sem.acquire(), timeout=settings.stt_queue_timeout_sec)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=503,
            detail={"error": {"code": "stt_busy", "message": "STT queue is full, try again"}},
        )

    try:
        result: STTResult = await engine.transcribe(data, language=language)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "bad_audio", "message": str(exc)}},
        )
    finally:
        sem.release()

    return STTResponse(
        text=result.text,
        language=result.language,
        confidence=result.confidence,
        duration_ms=result.duration_ms,
        latency_ms=result.latency_ms,
        model=result.model,
        truncated=result.truncated,
        no_speech=result.no_speech,
    )


def _supported_languages() -> set[str]:
    return {"en", "hi", "ml", "ta", "te", "kn", "bn", "mr", "gu"}
