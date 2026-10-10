"""
TwilioProvider — outbound calling via Twilio REST API.

Uses httpx directly (no twilio SDK dependency) so it works without
adding the twilio package to requirements.

Env vars required:
  TWILIO_ACCOUNT_SID   ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  TWILIO_AUTH_TOKEN    your auth token
  TWILIO_PHONE_NUMBER  +1xxxxxxxxxx  (your Twilio number)
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

_TWILIO_BASE = "https://api.twilio.com/2010-04-01"

# Twilio call status → our status
_STATUS_MAP: dict[str, tuple[str, str]] = {
    "completed":    ("completed",   "no_input"),
    "busy":         ("busy",        "busy"),
    "no-answer":    ("no_answer",   "no_answer"),
    "failed":       ("failed",      "failed"),
    "canceled":     ("canceled",    "failed"),
    "in-progress":  ("in_progress", ""),
    "ringing":      ("ringing",     ""),
    "queued":       ("queued",      ""),
    "initiated":    ("initiated",   ""),
}


class TwilioProvider(CallProvider):
    name = "twilio"

    def __init__(self) -> None:
        self._sid   = settings.twilio_account_sid.strip()
        self._token = settings.twilio_auth_token.strip()
        self._from  = settings.twilio_phone_number.strip()
        self._base  = f"{_TWILIO_BASE}/Accounts/{self._sid}"
        log.info("twilio_provider_init", sid=self._sid[:8] + "…")

    @property
    def _auth(self) -> tuple[str, str]:
        return (self._sid, self._token)

    async def place_call(self, req: PlaceCallRequest) -> PlaceCallResult:
        """Place an outbound call via Twilio Calls API."""
        caller_id = req.caller_id or self._from

        # Use Url parameter pointing to our flow webhook.
        # Twilio fetches this URL when the call is answered and executes the TwiML.
        # Do NOT use inline Twiml + StatusCallbackEvent together — disallowed on trial.
        payload: dict = {
            "To":                   req.to_number,
            "From":                 caller_id,
            "Url":                  req.flow_url,
            "Method":               "POST",
            "StatusCallback":       req.status_callback_url,
            "StatusCallbackMethod": "POST",
            "Timeout":              "30",
            "TimeLimit":            str(req.time_limit_sec or 120),
        }

        log.info("twilio_place_call_attempt",
                 to=req.to_number[-4:],
                 from_=caller_id,
                 base=self._base)

        async with httpx.AsyncClient(auth=self._auth, timeout=15.0) as client:
            resp = await client.post(
                f"{self._base}/Calls.json",
                data=payload,
            )
            log.info("twilio_api_response",
                     status_code=resp.status_code,
                     body=resp.text[:500])

            if not resp.is_success:
                log.error("twilio_call_failed",
                          status_code=resp.status_code,
                          body=resp.text)
                return PlaceCallResult(
                    provider_call_sid="",
                    accepted=False,
                    raw_status=f"http_{resp.status_code}: {resp.text[:500]}",
                )

        body = resp.json()
        sid = body.get("sid", "")
        raw_status = body.get("status", "initiated")

        log.info("twilio_place_call_result",
                 call_id=str(req.call_id),
                 sid=sid,
                 raw_status=raw_status,
                 accepted=bool(sid))

        return PlaceCallResult(
            provider_call_sid=sid,
            accepted=bool(sid),
            raw_status=raw_status,
        )

    async def hangup(self, provider_call_sid: str) -> None:
        try:
            async with httpx.AsyncClient(auth=self._auth, timeout=5.0) as client:
                resp = await client.post(
                    f"{self._base}/Calls/{provider_call_sid}.json",
                    data={"Status": "completed"},
                )
                resp.raise_for_status()
        except Exception as exc:
            log.warning("twilio_hangup_failed", sid=provider_call_sid, error=str(exc))

    def parse_webhook(
        self,
        kind: str,
        headers: Mapping,
        query: Mapping,
        body: Mapping,
    ) -> ProviderEvent:
        """Normalise Twilio POST webhook payload into ProviderEvent."""
        sid = str(body.get("CallSid", ""))
        raw_call_id = body.get("StatusCallbackEvent") or query.get("call_id")
        call_id: UUID | None = None
        if query.get("call_id"):
            try:
                call_id = UUID(str(query["call_id"]))
            except ValueError:
                pass

        raw_status = str(body.get("CallStatus", "")).lower().replace(" ", "-")
        our_status, _outcome = _STATUS_MAP.get(raw_status, ("failed", "failed"))

        data: dict = {}
        event_type: str

        if kind == "flow":
            event_type = "answered"
            digits = body.get("Digits", "")
            if digits:
                event_type = "dtmf"
                data = {"digits": digits}
        elif kind == "status":
            if raw_status == "ringing":
                event_type = "ringing"
            elif raw_status == "in-progress":
                event_type = "answered"
            elif raw_status in ("completed", "busy", "no-answer", "failed", "canceled"):
                event_type = "completed" if raw_status == "completed" else raw_status.replace("-", "_")
                data = {
                    "status": our_status,
                    "duration": int(body.get("CallDuration", 0) or 0),
                    "hangup_cause": raw_status,
                }
            else:
                event_type = "initiated"
        else:
            event_type = "failed"
            data = {"status": "failed", "duration": 0, "hangup_cause": "unknown"}

        stable = json.dumps({"status": raw_status, "sid": sid}, sort_keys=True)
        ikey = make_idempotency_key("twilio", sid, event_type, stable)

        return ProviderEvent(
            type=event_type,  # type: ignore[arg-type]
            provider_call_sid=sid,
            call_id=call_id,
            data=data,
            idempotency_key=ikey,
        )

    def render_steps(self, steps: list[CallStep]) -> str:  # type: ignore[override]
        """Render neutral steps to TwiML string."""
        parts = ['<?xml version="1.0" encoding="UTF-8"?><Response>']
        for step in steps:
            if isinstance(step, Play):
                parts.append(f'<Play>{step.audio_url}</Play>')
            elif isinstance(step, Gather):
                attrs = f'numDigits="{step.max_digits}" timeout="{step.timeout_sec}"'
                if step.finish_on_key:
                    attrs += f' finishOnKey="{step.finish_on_key}"'
                inner = ""
                if step.prompt_audio_url:
                    inner = f'<Play>{step.prompt_audio_url}</Play>'
                parts.append(f'<Gather {attrs}>{inner}</Gather>')
            elif isinstance(step, Record):
                parts.append(
                    f'<Record maxLength="{step.max_seconds}" '
                    f'timeout="{step.silence_timeout_sec}" '
                    f'playBeep="{"true" if step.play_beep else "false"}"/>'
                )
            elif isinstance(step, Hangup):
                parts.append('<Hangup/>')
        parts.append('</Response>')
        return "".join(parts)

    async def fetch_recording(self, url: str, dest: Path) -> Path:
        async with httpx.AsyncClient(auth=self._auth, timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(resp.content)
        return dest
