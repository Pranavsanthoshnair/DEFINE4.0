"""
Supabase REST client singleton for server-side backend operations.

Uses the service role key — never exposed to the browser.
All table operations go through PostgREST (no direct PG connection required).
"""
from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Return the shared Supabase client. Initialised once."""
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in the environment."
        )
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
