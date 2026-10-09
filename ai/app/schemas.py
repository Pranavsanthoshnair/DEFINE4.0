"""
Contract-exact Pydantic schemas for all AI service endpoints.
Fields, names, and types must not change without a contract-change PR.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


# ── /v1/stt ──────────────────────────────────────────────────────────────────

class STTResponse(BaseModel):
    text: str
    language: str
    confidence: float = Field(ge=0.0, le=1.0)
    duration_ms: int
    latency_ms: int
    model: str
    truncated: bool = False
    no_speech: bool = False


# ── /v1/intent ───────────────────────────────────────────────────────────────

IntentLabel = Literal[
    "confirm", "decline", "reschedule", "call_later", "stop_calling", "unclear"
]
IntentSource = Literal["rules", "model", "llm", "tap"]


class IntentRequest(BaseModel):
    text: str = Field(max_length=2000)
    language: str = Field(min_length=2, max_length=2)
    chosen_intent: IntentLabel | None = Field(
        default=None,
        description="Intent selected directly by a caller-facing tap",
    )
    allowed_intents: list[IntentLabel] = Field(
        default=[
            "confirm", "decline", "reschedule",
            "call_later", "stop_calling", "unclear",
        ]
    )


class IntentResponse(BaseModel):
    intent: IntentLabel
    confidence: float = Field(ge=0.0, le=1.0)
    source: IntentSource
    latency_ms: int


# ── /v1/speech-intent ────────────────────────────────────────────────────────

class SpeechIntentResponse(BaseModel):
    text: str
    language: str
    intent: IntentLabel
    confidence: float = Field(ge=0.0, le=1.0)
    source: IntentSource
    stt_model: str
    latency_ms: int
    no_speech: bool = False
    truncated: bool = False


# ── /v1/translate ─────────────────────────────────────────────────────────────

class TranslateRequest(BaseModel):
    segments: dict[str, str] = Field(
        description="segment_key -> text with {placeholder} variables"
    )
    source_language: str = Field(min_length=2, max_length=2)
    target_language: str = Field(min_length=2, max_length=2)


class TranslateResponse(BaseModel):
    segments: dict[str, str]
    model: str


# ── /v1/tts ──────────────────────────────────────────────────────────────────

class TTSRequest(BaseModel):
    text: str = Field(max_length=2000)
    language: str = Field(min_length=2, max_length=2)
    voice: Optional[str] = None


# ── /healthz ─────────────────────────────────────────────────────────────────

ModelStatus = Literal["loaded", "stub", "unavailable"]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    models: dict[str, ModelStatus]
