"""
Application configuration loaded from environment variables.
"""

from __future__ import annotations

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
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

    # ── Security ─────────────────────────────────────────────────────────────
    jwt_secret: str = "change-me-jwt-secret"
    data_enc_key: str = ""          # base64 32 bytes — AES-256-GCM
    phone_hmac_key: str = ""        # base64 32 bytes — HMAC-SHA256
    webhook_secret: str = "change-me-webhook-secret-32chars!!"

    # ── Storage ──────────────────────────────────────────────────────────────
    media_dir: str = "/data/media"
    recordings_dir: str = "/data/recordings"
    recording_retention_days: int = 30
    event_retention_days: int = 90

    # ── Telephony (M2) ────────────────────────────────────────────────────────
    call_provider: str = "mock"           # mock | exotel
    exotel_sid: str = ""
    exotel_api_key: str = ""
    exotel_api_token: str = ""
    exotel_subdomain: str = ""
    exotel_caller_id: str = ""
    exotel_max_concurrent: int = 3
    mock_speed: float = 1.0               # 0.1 = fast tests, 1.0 = normal

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
