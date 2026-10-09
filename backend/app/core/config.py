"""
Application configuration loaded from environment variables.
"""

from __future__ import annotations

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ─────────────────────────────────────────────────────────────────
    app_env: str = "dev"
    environment: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production"
    public_base_url: str = "http://localhost:8000"
    org_name: str = "Demo Institute"
    admin_email: str = "admin@example.com"
    admin_password: str = "change_this_admin_password_123"

    # ── CORS ────────────────────────────────────────────────────────────────
    cors_origins: List[str] = ["http://localhost:3000"]
    web_origin: str = "http://localhost:3000"

    # ── Database ────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/pr002"

    # ── Supabase ────────────────────────────────────────────────────────────
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # ── Redis / Celery ───────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Security & Blueprint Differentiators (H2, H3, H4) ────────────────────
    jwt_secret: str = "change-me-jwt-secret"
    data_enc_key: str = ""          # base64 32 bytes — AES-256-GCM
    phone_hmac_key: str = ""        # base64 32 bytes — HMAC-SHA256
    phone_hash_key: str = ""        # base64 32 bytes — lookup HMAC
    bloom_hmac_key: str = "change-me-bloom-hmac-key-secret-32b"  # Keyed Bloom filter HMAC key (H2)
    master_kek: str = "change-me-master-kek-32bytes-secret!!"    # Envelope encryption KEK (H3)
    keystore_dir: str = "/data/keystore"                         # Separate key-store path (H3)
    webhook_secret: str = "change-me-webhook-secret-32chars!!"
    sim_clock: bool = False                                      # Fast simulated clock (H14, H19)
    cost_per_minute: float = 0.60                                # Estimated INR telephony rate (H8)
    calling_window_default: str = "09:00-21:00"

    # ── Storage ──────────────────────────────────────────────────────────────
    media_dir: str = "/data/media"
    recordings_dir: str = "/data/recordings"
    recording_retention_days: int = 30
    event_retention_days: int = 90

    # ── Telephony (M2) ────────────────────────────────────────────────────────
    # auto = pick first available: exotel → twilio → mock
    call_provider: str = "auto"           # auto | mock | exotel | twilio
    exotel_sid: str = ""
    exotel_api_key: str = ""
    exotel_api_token: str = ""
    exotel_subdomain: str = ""
    exotel_caller_id: str = ""
    exotel_max_concurrent: int = 3
    # Twilio (alternative telephony)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    mock_speed: float = 1.0               # 0.1 = fast tests, 1.0 = normal

    # ── ElevenLabs ────────────────────────────────────────────────────────
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "EXAVITQu4vr4xnSDxMaL"  # Sarah — verified on free tier
    elevenlabs_model_id: str = "eleven_multilingual_v2"

    # ── Telegram ──────────────────────────────────────────────────────────
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    # Set to 'polling' for local dev, 'webhook' for production
    telegram_mode: str = "webhook"        # webhook | polling

    # ── AI Service ───────────────────────────────────────────────────────────
    ai_base_url: str = "http://localhost:8200"
    ai_internal_token: str = ""
    stt_model: str = "faster-whisper-small"
    llm_fallback: str = "none"            # gemini | groq | none
    gemini_api_key: str = ""
    groq_api_key: str = ""
    tts_engine: str = "edge"              # edge | parler

    # ── Legacy AI Provider ────────────────────────────────────────────────────
    ai_provider: str = "openai"
    ai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"

    # ── Webhook ─────────────────────────────────────────────────────────────
    webhook_base_url: str = "https://your-backend-url.example.com"


settings = Settings()
