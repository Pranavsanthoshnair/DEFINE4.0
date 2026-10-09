"""
Provider interface and neutral call step types.
Contract: CONTRACTS.md section 8.1
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Mapping
from uuid import UUID

from fastapi import Response


# ── Neutral Call Steps ───────────────────────────────────────────────────────

@dataclass
class Play:
    audio_url: str


@dataclass
class Gather:
    prompt_audio_url: str | None = None
    max_digits: int = 1
    timeout_sec: int = 6
    finish_on_key: str | None = None


@dataclass
class Record:
    max_seconds: int = 6
    silence_timeout_sec: int = 2
    play_beep: bool = True


@dataclass
class Hangup:
    pass


CallStep = Play | Gather | Record | Hangup


# ── Request / Result ─────────────────────────────────────────────────────────

@dataclass
class PlaceCallRequest:
    call_id: UUID
    to_number: str            # E.164, decrypted only inside this call
    caller_id: str            # ExoPhone
    status_callback_url: str
    flow_url: str             # URL the provider fetches when the callee answers
    custom_field: str         # str(call_id), echoed back by the provider
    time_limit_sec: int = 120


@dataclass
class PlaceCallResult:
    provider_call_sid: str
    accepted: bool
    raw_status: str


# ── Provider Event ────────────────────────────────────────────────────────────

@dataclass
class ProviderEvent:
    type: Literal[
        "initiated", "ringing", "answered", "amd_result",
        "dtmf", "recording_ready", "completed", "failed"
    ]
    provider_call_sid: str
    call_id: UUID | None      # from custom_field when present
    data: dict                # normalised: {"digits":"1"}, {"amd":"machine"},
                              # {"recording_url":"..."}, {"status":"busy","duration":12}
    idempotency_key: str


# ── Protocol ─────────────────────────────────────────────────────────────────

class CallProvider:
    """
    Interface for telephony providers.  Implementations: MockProvider, ExotelProvider.
    """
    name: str

    async def place_call(self, req: PlaceCallRequest) -> PlaceCallResult:
        raise NotImplementedError

    async def hangup(self, provider_call_sid: str) -> None:
        raise NotImplementedError

    def parse_webhook(
        self,
        kind: str,
        headers: Mapping,
        query: Mapping,
        body: Mapping,
    ) -> ProviderEvent:
        raise NotImplementedError

    def render_steps(self, steps: list[CallStep]) -> Response:
        """Turn neutral steps into whatever the provider expects."""
        raise NotImplementedError

    async def fetch_recording(self, url: str, dest: Path) -> Path:
        raise NotImplementedError


# ── Idempotency key helper ────────────────────────────────────────────────────

def make_idempotency_key(
    provider: str,
    provider_call_sid: str,
    event_type: str,
    stable_fields: str,
) -> str:
    """sha256(provider + provider_call_sid + event_type + stable_payload_fields)."""
    raw = f"{provider}|{provider_call_sid}|{event_type}|{stable_fields}"
    return hashlib.sha256(raw.encode()).hexdigest()
