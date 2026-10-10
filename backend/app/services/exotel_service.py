"""
ExotelService — real implementation for outbound call initiation and lookup.

This replaces the stub. All credentials come from settings (never from frontend).
Used by the /api/v1/capabilities/validate endpoint and the campaign engine.
"""

from __future__ import annotations

from typing import Optional

import httpx
import structlog

from app.core.config import settings

log = structlog.get_logger()


def _base_url() -> str:
    """Build Exotel base URL — handles plain subdomain, full hostname, or full URL."""
    sub = (settings.exotel_subdomain or "api.in.exotel.com").strip().rstrip("/")
    if "exotel.com" in sub:
        host = sub
    elif sub:
        host = f"{sub}.api.exotel.com"
    else:
        host = "api.in.exotel.com"
    # Strip any https:// the user may have accidentally typed
    host = host.removeprefix("https://").removeprefix("http://")
    return f"https://{host}/v1/Accounts/{settings.exotel_sid}"


def _auth() -> tuple[str, str]:
    return (settings.exotel_api_key, settings.exotel_api_token)


async def validate_credentials() -> dict:
    """
    Ping the Exotel Account details endpoint to verify credentials.
    Returns {"ok": True, "account": {...}} or {"ok": False, "error": "..."}
    Safe to call on startup or from the /validate endpoint.
    """
    if not all([
        settings.exotel_sid,
        settings.exotel_api_key,
        settings.exotel_api_token,
        settings.exotel_subdomain,
    ]):
        return {"ok": False, "error": "One or more Exotel credentials are empty in .env"}

    try:
        async with httpx.AsyncClient(auth=_auth(), timeout=8.0) as client:
            resp = await client.get(
                f"{_base_url()}.json",
            )
            if resp.status_code == 200:
                account = resp.json().get("Account", {})
                log.info("exotel_credentials_valid", sid=settings.exotel_sid)
                return {
                    "ok": True,
                    "account_sid": account.get("Sid", settings.exotel_sid),
                    "account_name": account.get("FriendlyName", ""),
                    "account_status": account.get("Status", ""),
                }
            elif resp.status_code == 401:
                return {"ok": False, "error": "Invalid API key or token (401 Unauthorized)"}
            elif resp.status_code == 404:
                return {"ok": False, "error": f"Account SID '{settings.exotel_sid}' not found (404)"}
            else:
                return {"ok": False, "error": f"Exotel returned HTTP {resp.status_code}: {resp.text[:200]}"}
    except httpx.ConnectError:
        return {"ok": False, "error": f"Cannot connect to {_base_url()} — check EXOTEL_SUBDOMAIN"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def place_call(
    to_number: str,
    caller_id: str,
    flow_url: str,
    status_callback_url: str,
    custom_field: str,
    time_limit_sec: int = 120,
) -> dict:
    """
    POST /Calls/connect — initiate an outbound call.
    Returns Exotel's response JSON on success.
    Raises httpx.HTTPStatusError on HTTP errors.
    """
    payload = {
        "From": caller_id,
        "To": to_number,
        "Url": flow_url,
        "StatusCallback": status_callback_url,
        "CustomField": custom_field,
        "TimeLimit": str(time_limit_sec),
        "Record": "false",
    }
    async with httpx.AsyncClient(auth=_auth(), timeout=10.0) as client:
        resp = await client.post(
            f"{_base_url()}/Calls/connect.json",
            data=payload,
        )
        resp.raise_for_status()
        return resp.json()


async def get_call_details(call_sid: str) -> dict:
    """
    GET /Calls/{CallSid} — fetch current call details.
    """
    async with httpx.AsyncClient(auth=_auth(), timeout=8.0) as client:
        resp = await client.get(f"{_base_url()}/Calls/{call_sid}.json")
        resp.raise_for_status()
        return resp.json()


async def hangup_call(call_sid: str) -> bool:
    """
    POST to update call Status=canceled — hangup a live call.
    Returns True if accepted.
    """
    try:
        async with httpx.AsyncClient(auth=_auth(), timeout=5.0) as client:
            resp = await client.post(
                f"{_base_url()}/Calls/{call_sid}.json",
                data={"Status": "canceled"},
            )
            return resp.status_code in (200, 204)
    except Exception as exc:
        log.error("exotel_hangup_failed", call_sid=call_sid, error=str(exc))
        return False
