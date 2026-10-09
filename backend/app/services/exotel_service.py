"""Service stub: Exotel outbound call initiation."""

from __future__ import annotations

import structlog
import httpx

from app.core.config import settings

log = structlog.get_logger()

EXOTEL_API_BASE = "https://{subdomain}.api.exotel.com/v1/Accounts/{sid}"


class ExotelService:
    """
    Wraps Exotel REST API calls.
    Credentials are read exclusively from settings (never from frontend).
    (Stub — HTTP calls NOT YET IMPLEMENTED.)
    """

    def __init__(self) -> None:
        self._base = EXOTEL_API_BASE.format(
            subdomain=settings.exotel_subdomain,
            sid=settings.exotel_sid,
        )
        self._auth = (settings.exotel_api_key, settings.exotel_api_token)

    async def initiate_call(self, to: str, call_flow_id: str) -> dict:
        """
        POST /Calls/connect — initiate an outbound call.
        Returns Exotel's response JSON.
        (NOT YET IMPLEMENTED.)
        """
        raise NotImplementedError("ExotelService.initiate_call is not implemented")

    async def get_call_details(self, call_sid: str) -> dict:
        """
        GET /Calls/{CallSid} — fetch call details.
        (NOT YET IMPLEMENTED.)
        """
        raise NotImplementedError("ExotelService.get_call_details is not implemented")
