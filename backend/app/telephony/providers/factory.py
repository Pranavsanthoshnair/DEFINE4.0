"""
Provider factory — auto-selects the best available telephony provider.

Resolution for CALL_PROVIDER=auto:
  1. Exotel  (if EXOTEL_API_KEY + EXOTEL_API_TOKEN + EXOTEL_SID all set)
  2. Twilio  (if TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN + TWILIO_PHONE_NUMBER set)
  3. Mock    (always available as safe fallback)
"""

from __future__ import annotations

import structlog

from app.core.config import settings
from app.telephony.providers.base import CallProvider

log = structlog.get_logger()


def _exotel_ready() -> bool:
    return all([settings.exotel_api_key, settings.exotel_api_token, settings.exotel_sid])


def _twilio_ready() -> bool:
    return all([
        settings.twilio_account_sid,
        settings.twilio_auth_token,
        settings.twilio_phone_number,
    ])


def get_provider() -> CallProvider:
    """
    Return the best available telephony provider.
    Never raises — always returns at least MockProvider.
    Removes lru_cache so credentials hot-reload works at startup.
    """
    from app.telephony.providers.mock import MockProvider

    mode = settings.call_provider.lower()

    if mode in ("exotel", "auto") and _exotel_ready():
        from app.telephony.providers.exotel import ExotelProvider
        log.info("telephony_provider", provider="exotel")
        return ExotelProvider()

    if mode in ("twilio", "auto") and _twilio_ready():
        try:
            from app.telephony.providers.twilio import TwilioProvider
            log.info("telephony_provider", provider="twilio")
            return TwilioProvider()
        except ImportError:
            log.warning("twilio_provider_import_failed", hint="pip install twilio")

    if mode == "exotel":
        log.warning("exotel_requested_but_credentials_missing_using_mock")
    elif mode == "twilio":
        log.warning("twilio_requested_but_credentials_missing_using_mock")

    log.info("telephony_provider", provider="mock")
    return MockProvider()


def active_provider_name() -> str:
    """Return the name of the active provider (safe, no secrets)."""
    mode = settings.call_provider.lower()
    if mode in ("exotel", "auto") and _exotel_ready():
        return "exotel"
    if mode in ("twilio", "auto") and _twilio_ready():
        return "twilio"
    return "mock"
