"""
Pydantic v2 request / response schemas for the AI service.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TranslateRequest(BaseModel):
    segments: dict[str, str]
    source_language: str
    target_language: str


class TranslateResponse(BaseModel):
    segments: dict[str, str]
    model: str = ""


class IntentRequest(BaseModel):
    text: str
    language: str
    allowed_intents: list[str]


class IntentResponse(BaseModel):
    intent: str
    confidence: float
    source: str  # rules | model | llm | tap
    latency_ms: int = 0


class SttResponse(BaseModel):
    text: str
    language: str
    confidence: float
    duration_ms: int
    latency_ms: int
    model: str = ""


class SpeechIntentResponse(BaseModel):
    text: str
    language: str
    intent: str
    confidence: float
    source: str
    stt_model: str = ""
    latency_ms: int = 0
    no_speech: bool = False
