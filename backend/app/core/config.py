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
    environment: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production"

    # ── CORS ────────────────────────────────────────────────────────────────
    cors_origins: List[str] = ["http://localhost:3000"]

    # ── Supabase ────────────────────────────────────────────────────────────
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    database_url: str = ""

    # ── Exotel ──────────────────────────────────────────────────────────────
    exotel_sid: str = ""
    exotel_api_key: str = ""
    exotel_api_token: str = ""
    exotel_subdomain: str = ""
    exotel_caller_id: str = ""

    # ── AI Provider ─────────────────────────────────────────────────────────
    ai_provider: str = "openai"          # openai | anthropic | gemini
    ai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"

    # ── Webhook ─────────────────────────────────────────────────────────────
    webhook_base_url: str = "https://your-backend-url.example.com"


settings = Settings()
