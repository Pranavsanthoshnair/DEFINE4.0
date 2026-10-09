"""
Veylo AI Service — config.
All settings are read from environment variables.
"""

from __future__ import annotations

from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Service ──────────────────────────────────────────────────────────────
    environment: str = "development"
    port: int = 8200

    # ── Auth ─────────────────────────────────────────────────────────────────
    ai_internal_token: str = "change-me-in-production"

    # ── Stub mode ────────────────────────────────────────────────────────────
    # Set AI_STUB=true so M1/M2 are never blocked before credentials are ready
    ai_stub: bool = True

    # ── Sarvam AI ─────────────────────────────────────────────────────────────
    # Primary provider for STT, translate, and TTS.
    # Key is kept server-side only — never forwarded to frontend.
    sarvam_api_key: str = ""
    sarvam_stt_model: str = "saaras:v4"
    sarvam_translate_model: str = "mayura:v1"
    sarvam_tts_model: str = "bulbul:v2"
    # Sample rate for TTS output — 8000 Hz for Exotel telephony
    sarvam_tts_sample_rate: int = 8000

    # Exotel audio format: "auto" | "pcm_s16le" | "wav" | "mp3" | "amr"
    # Set to "pcm_s16le" if Exotel sends raw PCM (must also be 16kHz)
    exotel_audio_codec: str = "auto"

    # ── Intent ───────────────────────────────────────────────────────────────
    intent_confidence_threshold: float = 0.6
    # Optional LLM fallback for intent when rules give no match: none | gemini | groq
    llm_fallback: Literal["none", "gemini", "groq"] = "none"
    gemini_api_key: str = ""
    groq_api_key: str = ""
    # Groq STT model — whisper-large-v3-turbo (fastest) or whisper-large-v3 (most accurate)
    groq_stt_model: str = "whisper-large-v3-turbo"

    # ── STT provider routing ──────────────────────────────────────────────────
    # sarvam → always Sarvam Saaras v4
    # groq   → always Groq Whisper Large v3 Turbo
    # auto   → race both concurrently, return first winner, fallback if one fails
    stt_provider: str = "auto"


    # ── Lexicon ───────────────────────────────────────────────────────────────
    lexicon_dir: str = "app/intent/lexicon"

    # ── Legacy local-model settings (kept for reference, not used in MVP) ──────
    # These are no longer active. Sarvam is the primary provider.
    # whisper_model_size: str = "small"
    # indictrans_model: str = "ai4bharat/indictrans2-en-indic-dist-200M"
    # tts_engine: str = "stub"
    models_dir: str = "/models"


settings = Settings()
