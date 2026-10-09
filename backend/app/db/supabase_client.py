"""
Supabase REST client singleton for server-side backend operations.

Uses the service role key — never exposed to the browser.
All table operations go through PostgREST (no direct PG connection required).
"""
from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


def is_supabase_configured() -> bool:
    """Return True if Supabase credentials are valid and not placeholders."""
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return False
    url = settings.supabase_url.lower()
    key = settings.supabase_service_role_key.lower()
    if "xxxx" in url or "example" in url or "change" in key:
        return False
    return True


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Return the shared Supabase client. Initialised once."""
    if not is_supabase_configured():
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in the environment."
        )
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
