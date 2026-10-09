"""
TwilioProvider — Outbound Calling and Webhook Integration for Twilio.

Implements the CallProvider interface using Twilio's Voice REST API and TwiML.
Normalizes caller IDs, handles status callbacks, and renders TwiML for dynamic voice flows.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping
from uuid import UUID

import httpx
import structlog
from fastapi import Response

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


def _normalize_phone_for_twilio(num: str) -> str:
    """Ensure phone number is in valid E.164 format for Twilio."""
    cleaned = re.sub(r"[\s\-\(\)\.]+", "", num.strip())
    if cleaned.startswith("+"):
        return cleaned
    if cleaned.startswith("0") and len(cleaned) == 11:
        cleaned = cleaned[1:]
    if len(cleaned) == 10 and cleaned.isdigit():
        return f"+91{cleaned}"
    if cleaned.isdigit():
        return f"+{cleaned}"
    return cleaned


# Status mapping from Twilio CallStatus -> internal status and outcome
_TWILIO_STATUS_MAP: dict[str, tuple[str, str]] = {
    "queued": ("queued", ""),
    "initiated": ("initiated", ""),
    "ringing": ("ringing", ""),
    "in-progress": ("in_progress", ""),
    "completed": ("completed", "completed"),
    "busy": ("busy", "busy"),
    "no-answer": ("no_answer", "no_answer"),
    "canceled": ("canceled", "failed"),
    "failed": ("failed", "failed"),
}


class TwilioProvider(CallProvider):
    """Production Twilio telephony provider."""

    name = "twilio"

    def __init__(self) -> None:
        self._account_sid = settings.twilio_account_sid
        self._auth_token = settings.twilio_auth_token
        self._caller_id = _normalize_phone_for_twilio(settings.twilio_phone_number)
        self._base_url = f"https://api.twilio.com/2010-04-01/Accounts/{self._account_sid}"

    @property
    def _auth(self) -> tuple[str, str]:
        return (self._account_sid, self._auth_token)

    async def place_call(self, req: PlaceCallRequest) -> PlaceCallResult:
        """Place an outbound call via Twilio Voice API."""
        from_number = _normalize_phone_for_twilio(req.caller_id or self._caller_id)
        to_number = _normalize_phone_for_twilio(req.to_number)

        payload = {
            "From": from_number,
            "To": to_number,
            "Url": req.flow_url,
            "StatusCallback": req.status_callback_url,
            "StatusCallbackEvent": ["initiated", "ringing", "answered", "completed"],
            "Timeout": req.time_limit_sec,
        }

        url = f"{self._base_url}/Calls.json"

        try:
            async with httpx.AsyncClient(auth=self._auth, timeout=12.0) as client:
                resp = await client.post(url, data=payload)

            if resp.status_code in (200, 201):
                data = resp.json()
                call_sid = data.get("sid", "")
                raw_status = data.get("status", "queued")
                log.info(
                    "twilio_call_placed",
                    call_sid=call_sid,
                    to=to_number[:6] + "...",
                    status=raw_status,
                )
                return PlaceCallResult(
                    provider_call_sid=call_sid,
                    accepted=True,
                    raw_status=raw_status,
                )

            log.error(
                "twilio_call_failed",
                status_code=resp.status_code,
                body=resp.text,
            )
            return PlaceCallResult(
                provider_call_sid="",
                accepted=False,
                raw_status=f"http_{resp.status_code}: {resp.text[:100]}",
            )

        except Exception as exc:
            log.exception("twilio_place_call_exception", error=str(exc))
            return PlaceCallResult(
                provider_call_sid="",
                accepted=False,
                raw_status=f"exception: {exc}",
            )

    async def hangup(self, provider_call_sid: str) -> None:
        """Terminate an active call."""
        url = f"{self._base_url}/Calls/{provider_call_sid}.json"
        try:
            async with httpx.AsyncClient(auth=self._auth, timeout=8.0) as client:
                await client.post(url, data={"Status": "completed"})
            log.info("twilio_hangup_success", call_sid=provider_call_sid)
        except Exception as exc:
            log.warning("twilio_hangup_failed", call_sid=provider_call_sid, error=str(exc))

    def parse_webhook(
        self,
        kind: str,
        headers: Mapping,
        query: Mapping,
        body: Mapping,
    ) -> ProviderEvent:
        """Parse incoming webhook event from Twilio."""
        call_sid = str(body.get("CallSid") or query.get("CallSid") or "")
        call_status = str(body.get("CallStatus") or query.get("CallStatus") or "").lower()
        digits = body.get("Digits")
        recording_url = body.get("RecordingUrl")
        answered_by = str(body.get("AnsweredBy") or "").lower()

        # Custom call_id if passed via query/param
        custom_id_raw = query.get("call_id") or body.get("CustomField")
        call_id: UUID | None = None
        if custom_id_raw:
            try:
                call_id = UUID(str(custom_id_raw))
            except ValueError:
                pass

        data: dict = {}

        if digits is not None:
            event_type = "dtmf"
            data["digits"] = str(digits)
        elif recording_url:
            event_type = "recording_ready"
            data["recording_url"] = str(recording_url)
            data["recording_sid"] = str(body.get("RecordingSid") or "")
        elif answered_by in ("machine_start", "machine_end_beep", "machine_end_silence", "machine_end_other"):
            event_type = "amd_result"
            data["amd"] = "machine"
        elif answered_by == "human":
            event_type = "amd_result"
            data["amd"] = "human"
        elif call_status in ("completed", "busy", "no-answer", "canceled", "failed"):
            mapped_status, mapped_outcome = _TWILIO_STATUS_MAP.get(call_status, ("completed", ""))
            event_type = "completed" if mapped_status == "completed" else "failed"
            data["status"] = mapped_status
            data["outcome"] = mapped_outcome
            duration = body.get("CallDuration") or body.get("Duration")
            if duration:
                try:
                    data["duration"] = int(duration)
                except (ValueError, TypeError):
                    pass
        elif call_status == "in-progress":
            event_type = "answered"
            data["status"] = "in_progress"
        elif call_status == "ringing":
            event_type = "ringing"
            data["status"] = "ringing"
        else:
            event_type = "initiated"
            data["status"] = call_status

        stable = f"{call_status}|{digits or ''}|{recording_url or ''}"
        idem_key = make_idempotency_key(self.name, call_sid, event_type, stable)

        return ProviderEvent(
            type=event_type,
            provider_call_sid=call_sid,
            call_id=call_id,
            data=data,
            idempotency_key=idem_key,
        )

    def render_steps(self, steps: list[CallStep]) -> Response:
        """Render CallStep sequence as standard TwiML XML."""
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<Response>"]

        for step in steps:
            if isinstance(step, Play):
                xml_lines.append(f'  <Play>{step.audio_url}</Play>')
            elif isinstance(step, Gather):
                gather_attrs = [f'numDigits="{step.max_digits}"', f'timeout="{step.timeout_sec}"']
                if step.finish_on_key:
                    gather_attrs.append(f'finishOnKey="{step.finish_on_key}"')
                xml_lines.append(f'  <Gather {" ".join(gather_attrs)}>')
                if step.prompt_audio_url:
                    xml_lines.append(f'    <Play>{step.prompt_audio_url}</Play>')
                xml_lines.append("  </Gather>")
            elif isinstance(step, Record):
                rec_attrs = [
                    f'maxLength="{step.max_seconds}"',
                    f'playBeep="{"true" if step.play_beep else "false"}"',
                    f'timeout="{step.silence_timeout_sec}"',
                ]
                xml_lines.append(f'  <Record {" ".join(rec_attrs)}/>')
            elif isinstance(step, Hangup):
                xml_lines.append("  <Hangup/>")

        xml_lines.append("</Response>")
        return Response(content="\n".join(xml_lines), media_type="application/xml")

    async def fetch_recording(self, url: str, dest: Path) -> Path:
        """Download remote recording audio from Twilio."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Twilio recordings append .wav or .mp3
        download_url = url if url.endswith((".wav", ".mp3")) else f"{url}.wav"
        async with httpx.AsyncClient(auth=self._auth, timeout=30.0) as client:
            resp = await client.get(download_url)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
        return dest
