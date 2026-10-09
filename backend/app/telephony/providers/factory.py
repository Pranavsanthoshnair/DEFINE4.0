"""
Provider factory — reads CALL_PROVIDER env var and returns the right instance.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.telephony.providers.base import CallProvider


@lru_cache(maxsize=1)
def get_provider() -> CallProvider:
    """Return the configured telephony provider (singleton per process)."""
    provider_name = settings.call_provider.lower()
    if provider_name == "mock":
        from app.telephony.providers.mock import MockProvider
        return MockProvider()
    elif provider_name == "exotel":
        from app.telephony.providers.exotel import ExotelProvider
        return ExotelProvider()
    else:
        raise ValueError(
            f"Unknown CALL_PROVIDER={provider_name!r}. Use 'mock' or 'exotel'."
        )
