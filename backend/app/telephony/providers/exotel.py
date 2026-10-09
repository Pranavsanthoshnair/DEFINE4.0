"""
ExotelProvider — stub implementation for Phase 2.

All Exotel field names are declared in the CONSTANTS block at the top so
any mismatch is a single-line fix.  Do NOT add field names anywhere else.

VERIFY AT KICKOFF (answers go in CONTRACTS.md section 8.3):
  1. integration_mode: dynamic (flow URL) or static (dashboard flow)?
  2. CustomField parameter name that echoes our call_id.
  3. AMD availability and delivery mechanism.
  4. Can we get speech during the call (sync) or only after (async)?
  5. Audio format required (wav 8kHz mono / mp3).
  6. Sandbox limits.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping
from uuid import UUID

import httpx
import structlog

from app.core.config import settings
from app.telephony.providers.base import (
    CallProvider,
    CallStep,
    Gather,
    Hangup,
    Play,
    PlaceCallRequest,
    PlaceCallResult,
    ProviderEvent,
    Record,
    make_idempotency_key,
)

log = structlog.get_logger()

# ── CONSTANTS — all Exotel field names live here ──────────────────────────────
# Update this block after kickoff verification; do not scatter field names.

_FIELD_CALL_SID = "CallSid"
_FIELD_STATUS = "Status"
_FIELD_DURATION = "Duration"
_FIELD_FROM = "From"
_FIELD_TO = "To"
_FIELD_CUSTOM_FIELD = "CustomField"   # VERIFY: echoes our call_id
_FIELD_AMD_RESULT = "AmdResult"       # VERIFY: field name for AMD
_FIELD_RECORDING_URL = "RecordingUrl"
_FIELD_DIGITS = "Digits"
_FIELD_HANGUP_CAUSE = "HangupCause"
_FIELD_DIRECTION = "Direction"

# Exotel status → our call status / outcome
_STATUS_MAP: dict[str, tuple[str, str]] = {
    "completed":  ("completed", "no_input"),    # outcome refined by intent
    "busy":       ("busy",      "busy"),
    "no-answer":  ("no_answer", "no_answer"),
    "failed":     ("failed",    "failed"),
    "canceled":   ("canceled",  "failed"),
    "in-progress":("in_progress", ""),
    "ringing":    ("ringing",   ""),
}


class ExotelProvider(CallProvider):
    """Exotel telephony provider.  Implement after kickoff VERIFY answers."""

    name = "exotel"

    def __init__(self) -> None:
        self._sid = settings.exotel_sid
        self._key = settings.exotel_api_key
        self._token = settings.exotel_api_token
        self._subdomain = settings.exotel_subdomain
        self._base_url = (
            f"https://{settings.exotel_subdomain}.api.exotel.com/v1/Accounts/{self._sid}"
        )

    @property
    def _auth(self) -> tuple[str, str]:
        return (self._key, self._token)

    async def place_call(self, req: PlaceCallRequest) -> PlaceCallResult:
        """
        Initiate an outbound call via Exotel.
        VERIFY: confirm parameter names from official docs before enabling.
        """
        payload = {
            "From": req.caller_id,
            "To": req.to_number,
            "Url": req.flow_url,           # dynamic mode
            "StatusCallback": req.status_callback_url,
            _FIELD_CUSTOM_FIELD: req.custom_field,
            "TimeLimit": req.time_limit_sec,
        }
        async with httpx.AsyncClient(auth=self._auth, timeout=10.0) as client:
            resp = await client.post(
                f"{self._base_url}/Calls/connect.json",
                data=payload,
            )
            resp.raise_for_status()
            body = resp.json()

        call_data = body.get("Call", {})
        sid = call_data.get(_FIELD_CALL_SID, "")
        raw_status = call_data.get(_FIELD_STATUS, "initiated")

        log.info(
            "exotel_place_call",
            call_id=str(req.call_id),
            sid=sid,
            raw_status=raw_status,
        )
        return PlaceCallResult(
            provider_call_sid=sid,
            accepted=bool(sid),
            raw_status=raw_status,
        )

    async def hangup(self, provider_call_sid: str) -> None:
        async with httpx.AsyncClient(auth=self._auth, timeout=5.0) as client:
            await client.post(
                f"{self._base_url}/Calls/{provider_call_sid}.json",
                data={"Status": "canceled"},
            )

    def parse_webhook(
        self,
        kind: str,
        headers: Mapping,
        query: Mapping,
        body: Mapping,
    ) -> ProviderEvent:
        """Normalise Exotel form/JSON payload into ProviderEvent."""
        sid = body.get(_FIELD_CALL_SID, "")
        raw_call_id = body.get(_FIELD_CUSTOM_FIELD) or query.get("call_id")
        call_id: UUID | None = None
        if raw_call_id:
            try:
                call_id = UUID(str(raw_call_id))
            except ValueError:
                pass

        raw_status = body.get(_FIELD_STATUS, "").lower().replace(" ", "-")
        our_status, _outcome = _STATUS_MAP.get(raw_status, ("failed", "failed"))

        data: dict = {}
        event_type: str

        if kind == "flow":
            event_type = "answered"
            amd_raw = body.get(_FIELD_AMD_RESULT, "")
            if amd_raw:
                event_type = "amd_result"
                data = {"amd": amd_raw.lower()}
            digits = body.get(_FIELD_DIGITS, "")
            if digits:
                event_type = "dtmf"
                data = {"digits": digits}
        elif kind == "input":
            event_type = "dtmf"
            data = {"digits": body.get(_FIELD_DIGITS, "")}
        elif kind == "recording":
            event_type = "recording_ready"
            data = {"recording_url": body.get(_FIELD_RECORDING_URL, "")}
        else:  # status
            if raw_status in ("ringing",):
                event_type = "ringing"
            elif raw_status == "in-progress":
                event_type = "answered"
            elif raw_status in ("completed", "busy", "no-answer", "failed", "canceled"):
                event_type = "completed" if raw_status == "completed" else raw_status.replace("-", "_")
                data = {
                    "status": our_status,
                    "duration": int(body.get(_FIELD_DURATION, 0)),
                    "hangup_cause": body.get(_FIELD_HANGUP_CAUSE, ""),
                }
            else:
                event_type = "failed"
                data = {"status": "failed", "duration": 0, "hangup_cause": "unknown"}

        # Build idempotency key from immutable fields
        timestamp_field = body.get("StartTime", body.get("DateCreated", ""))
        stable = json.dumps(
            {"status": raw_status, "ts": timestamp_field}, sort_keys=True
        )
        ikey = make_idempotency_key("exotel", sid, event_type, stable)

        return ProviderEvent(
            type=event_type,  # type: ignore[arg-type]
            provider_call_sid=sid,
            call_id=call_id,
            data=data,
            idempotency_key=ikey,
        )

    def render_steps(self, steps: list[CallStep]) -> dict:
        """
        Render neutral steps to Exotel's dynamic-mode response format.
        VERIFY: confirm the exact JSON/XML schema Exotel expects from a dynamic URL.
        """
        rendered = []
        for step in steps:
            if isinstance(step, Play):
                rendered.append({"action": "play", "url": step.audio_url})
            elif isinstance(step, Gather):
                node: dict = {
                    "action": "gather",
                    "maxDigits": step.max_digits,
                    "timeoutMs": step.timeout_sec * 1000,
                }
                if step.prompt_audio_url:
                    node["playUrl"] = step.prompt_audio_url
                rendered.append(node)
            elif isinstance(step, Record):
                rendered.append(
                    {
                        "action": "record",
                        "maxLength": step.max_seconds,
                        "silenceTimeout": step.silence_timeout_sec,
                        "playBeep": step.play_beep,
                    }
                )
            elif isinstance(step, Hangup):
                rendered.append({"action": "hangup"})
        return {"flow": rendered}

    async def fetch_recording(self, url: str, dest: Path) -> Path:
        """Download recording with Exotel auth, write to dest."""
        async with httpx.AsyncClient(auth=self._auth, timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(resp.content)
        return dest
