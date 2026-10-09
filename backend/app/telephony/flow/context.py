"""
Flow context dataclass and event types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID


# ── Template view (snapshot of what the engine needs) ────────────────────────

@dataclass
class TemplateView:
    dtmf_map: dict[str, str]        # e.g. {"1":"confirm","2":"decline","9":"stop_calling"}
    speech_enabled: bool
    voicemail_policy: Literal["leave_message", "skip_and_retry"]


# ── Call context (loaded from DB, passed into the engine) ─────────────────────

@dataclass
class CallContext:
    call_id: UUID
    language: str                   # ISO 639-1 e.g. "en", "hi"
    amd_result: str | None          # human | machine | unknown | None
    flow_state: dict                # reprompts, no_input_count, speech_attempts, branch
    template: TemplateView
    audio: dict[str, str]           # segment_key -> public wav URL for this language
    speech_threshold: float = 0.6


# ── Events ────────────────────────────────────────────────────────────────────

@dataclass
class Answered:
    pass


@dataclass
class AmdResult:
    value: Literal["human", "machine", "unknown"]


@dataclass
class Digits:
    value: str


@dataclass
class Timeout:
    pass


@dataclass
class RecordingReady:
    url: str


@dataclass
class SpeechResult:
    text: str
    intent: str
    confidence: float
    source: str = "speech"
    stt_model: str | None = None
    latency_ms: int | None = None


@dataclass
class Completed:
    status: str           # no_answer | busy | failed | canceled | completed
    duration: int = 0
    hangup_cause: str = ""


# Union type for all events
FlowEvent = (
    Answered | AmdResult | Digits | Timeout
    | RecordingReady | SpeechResult | Completed
)


# ── Intent result ─────────────────────────────────────────────────────────────

@dataclass
class IntentResult:
    label: str
    confidence: float
    source: Literal["dtmf", "speech"]
    raw_input: str
    step_key: str = "prompt"
    stt_model: str | None = None
    latency_ms: int | None = None


# ── Flow decision (what the engine returns) ───────────────────────────────────

@dataclass
class FlowDecision:
    steps: list                    # list[CallStep]
    intent: IntentResult | None = None
    outcome: str | None = None
    finalize: bool = False
    new_flow_state: dict = field(default_factory=dict)
    opt_out: bool = False
