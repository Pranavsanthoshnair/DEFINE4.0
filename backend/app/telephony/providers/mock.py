"""
MockProvider — works with no network.

The mock decides behaviour from the last two digits of the phone number
(CONTRACTS.md section 9.6).  It schedules a Celery task to simulate real
webhook callbacks so the full pipeline is exercised.
"""

from __future__ import annotations

import asyncio
import json
import uuid
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

# ── Scenario table (CONTRACTS.md 9.6) ────────────────────────────────────────

SCENARIOS: dict[str, str] = {
    "01": "human_press_1",
    "02": "human_press_2",
    "03": "no_answer",
    "04": "busy",
    "05": "voicemail",
    "06": "hangup_during_prompt",
    "07": "speech_yes",
    "08": "unclear_then_press_1",
    "09": "press_9_stop",
    "10": "silence_twice",
}


def _suffix(phone: str) -> str:
    """Return the last two digits of the phone number."""
    digits = "".join(c for c in phone if c.isdigit())
    return digits[-2:] if len(digits) >= 2 else "00"


class MockProvider(CallProvider):
    """Simulates telephony without making any real calls."""

    name = "mock"

    async def place_call(self, req: PlaceCallRequest) -> PlaceCallResult:
        sid = f"mock-{uuid.uuid4().hex[:16]}"
        log.info(
            "mock_place_call",
            call_id=str(req.call_id),
            sid=sid,
            phone_last4=req.to_number[-4:],
        )
        # Schedule the simulator as a background asyncio task.
        # In a real worker environment this is a Celery task.
        asyncio.create_task(
            _simulate(
                sid=sid,
                call_id=req.call_id,
                phone=req.to_number,
                flow_url=req.flow_url,
                status_callback_url=req.status_callback_url,
            )
        )
        return PlaceCallResult(
            provider_call_sid=sid,
            accepted=True,
            raw_status="initiated",
        )

    async def hangup(self, provider_call_sid: str) -> None:
        log.debug("mock_hangup", sid=provider_call_sid)

    def parse_webhook(
        self,
        kind: str,
        headers: Mapping,
        query: Mapping,
        body: Mapping,
    ) -> ProviderEvent:
        """Parse a mock webhook payload into a ProviderEvent."""
        event_type = body.get("event_type", kind)
        sid = body.get("provider_call_sid", body.get("CallSid", ""))
        raw_call_id = body.get("call_id") or query.get("call_id")
        call_id: UUID | None = None
        if raw_call_id:
            try:
                call_id = UUID(str(raw_call_id))
            except ValueError:
                pass

        data: dict = {}
        if event_type in ("dtmf", "input"):
            data = {"digits": body.get("digits", "")}
        elif event_type == "amd_result":
            data = {"amd": body.get("amd", "unknown")}
        elif event_type == "recording_ready":
            data = {"recording_url": body.get("recording_url", "")}
        elif event_type in ("completed", "failed", "no_answer", "busy"):
            data = {
                "status": body.get("status", event_type),
                "duration": int(body.get("duration", 0)),
                "hangup_cause": body.get("hangup_cause", ""),
            }

        stable = json.dumps(data, sort_keys=True)
        ikey = make_idempotency_key("mock", sid, event_type, stable)

        return ProviderEvent(
            type=event_type,  # type: ignore[arg-type]
            provider_call_sid=sid,
            call_id=call_id,
            data=data,
            idempotency_key=ikey,
        )

    def render_steps(self, steps: list[CallStep]) -> dict:
        """Return a simple JSON representation of the steps."""
        rendered = []
        for step in steps:
            if isinstance(step, Play):
                rendered.append({"action": "play", "url": step.audio_url})
            elif isinstance(step, Gather):
                rendered.append(
                    {
                        "action": "gather",
                        "prompt_url": step.prompt_audio_url,
                        "max_digits": step.max_digits,
                        "timeout_sec": step.timeout_sec,
                    }
                )
            elif isinstance(step, Record):
                rendered.append(
                    {
                        "action": "record",
                        "max_seconds": step.max_seconds,
                        "silence_timeout_sec": step.silence_timeout_sec,
                    }
                )
            elif isinstance(step, Hangup):
                rendered.append({"action": "hangup"})
        return {"steps": rendered}

    async def fetch_recording(self, url: str, dest: Path) -> Path:
        """Download a recording from a local fixture URL."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            resp.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(resp.content)
        return dest


# ── Simulator coroutine ────────────────────────────────────────────────────────

async def _simulate(
    sid: str,
    call_id: UUID,
    phone: str,
    flow_url: str,
    status_callback_url: str,
) -> None:
    """
    Simulate a call by posting to the real webhook endpoints.
    Behaviour is determined by the last two digits of the phone number.
    """
    speed = settings.mock_speed
    delay = 0.2 * speed

    scenario = SCENARIOS.get(_suffix(phone), "random")
    log.info("mock_simulator_start", sid=sid, scenario=scenario, phone_last4=phone[-4:])

    base_url = settings.public_base_url
    secret = settings.webhook_secret

    async with httpx.AsyncClient(timeout=10.0) as client:
        # ── Ringing ──────────────────────────────────────────────────────────
        await _post_status(client, status_callback_url, sid, call_id, "ringing", 0)
        await asyncio.sleep(delay)

        if scenario == "no_answer":
            await _post_status(client, status_callback_url, sid, call_id, "no_answer", 0)
            return

        if scenario == "busy":
            await _post_status(client, status_callback_url, sid, call_id, "busy", 0)
            return

        # ── Answered ─────────────────────────────────────────────────────────
        await _post_status(client, status_callback_url, sid, call_id, "answered", 0)
        await asyncio.sleep(delay)

        if scenario == "voicemail":
            await _post_flow_event(client, flow_url, sid, call_id, "amd_result", {"amd": "machine"})
            await asyncio.sleep(delay)
            await _post_status(client, status_callback_url, sid, call_id, "completed", 5)
            return

        # Human answer scenarios
        await _post_flow_event(client, flow_url, sid, call_id, "amd_result", {"amd": "human"})
        await asyncio.sleep(delay * 2)  # caller hears the greeting

        if scenario == "hangup_during_prompt":
            await _post_status(client, status_callback_url, sid, call_id, "completed", 3,
                               hangup_cause="caller_hangup")
            return

        if scenario == "human_press_1":
            await _post_dtmf(client, flow_url, sid, call_id, "1")
        elif scenario == "human_press_2":
            await _post_dtmf(client, flow_url, sid, call_id, "2")
        elif scenario == "press_9_stop":
            await _post_dtmf(client, flow_url, sid, call_id, "9")
        elif scenario == "silence_twice":
            # First silence
            await _post_flow_event(client, flow_url, sid, call_id, "dtmf", {"digits": ""})
            await asyncio.sleep(delay)
            # Second silence
            await _post_flow_event(client, flow_url, sid, call_id, "dtmf", {"digits": ""})
        elif scenario == "speech_yes":
            lang = "en"  # default; ideally extracted from context
            fixture_url = (
                f"{base_url}/media/fixtures/audio/yes_{lang}.wav"
            )
            await _post_flow_event(
                client, flow_url, sid, call_id,
                "recording_ready", {"recording_url": fixture_url}
            )
        elif scenario == "unclear_then_press_1":
            # Post a recording with low confidence (unclear)
            fixture_url = f"{base_url}/media/fixtures/audio/noise.wav"
            await _post_flow_event(
                client, flow_url, sid, call_id,
                "recording_ready", {"recording_url": fixture_url}
            )
            await asyncio.sleep(delay)
            # Then press 1
            await _post_dtmf(client, flow_url, sid, call_id, "1")
        else:
            # random / unknown → press 1
            await _post_dtmf(client, flow_url, sid, call_id, "1")

        await asyncio.sleep(delay)
        await _post_status(client, status_callback_url, sid, call_id, "completed", 20)


async def _post_status(
    client: httpx.AsyncClient,
    url: str,
    sid: str,
    call_id: UUID,
    status: str,
    duration: int,
    hangup_cause: str = "",
) -> None:
    body = {
        "event_type": status,
        "provider_call_sid": sid,
        "call_id": str(call_id),
        "status": status,
        "duration": duration,
        "hangup_cause": hangup_cause,
    }
    try:
        await client.post(url, json=body)
    except Exception as exc:  # noqa: BLE001
        log.warning("mock_post_status_failed", error=str(exc), status=status)


async def _post_flow_event(
    client: httpx.AsyncClient,
    url: str,
    sid: str,
    call_id: UUID,
    event_type: str,
    data: dict,
) -> None:
    body = {
        "event_type": event_type,
        "provider_call_sid": sid,
        "call_id": str(call_id),
        **data,
    }
    try:
        await client.post(url, json=body, params={"call_id": str(call_id)})
    except Exception as exc:  # noqa: BLE001
        log.warning("mock_post_flow_event_failed", error=str(exc), event_type=event_type)


async def _post_dtmf(
    client: httpx.AsyncClient,
    url: str,
    sid: str,
    call_id: UUID,
    digit: str,
) -> None:
    await _post_flow_event(client, url, sid, call_id, "dtmf", {"digits": digit})
