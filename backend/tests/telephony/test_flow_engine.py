"""
Unit tests for the flow engine.

Covers every row in CONTRACTS.md section 9.2 and additional edge cases.
No I/O — the engine is a pure function.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from app.telephony.flow.context import (
    Answered,
    AmdResult,
    CallContext,
    Completed,
    Digits,
    FlowDecision,
    RecordingReady,
    SpeechResult,
    TemplateView,
    Timeout,
)
from app.telephony.flow.engine import next as flow_next
from app.telephony.providers.base import Gather, Hangup, Play, Record


# ── Test fixture factories ────────────────────────────────────────────────────

def make_ctx(
    amd_result=None,
    flow_state=None,
    speech_enabled=False,
    voicemail_policy="skip_and_retry",
    dtmf_map=None,
    speech_threshold=0.6,
) -> CallContext:
    if dtmf_map is None:
        dtmf_map = {"1": "confirm", "2": "decline", "3": "reschedule", "9": "stop_calling"}
    if flow_state is None:
        flow_state = {}
    audio = {
        "greeting": "https://example.com/greeting.wav",
        "prompt": "https://example.com/prompt.wav",
        "reprompt": "https://example.com/reprompt.wav",
        "ack_confirm": "https://example.com/ack_confirm.wav",
        "ack_decline": "https://example.com/ack_decline.wav",
        "ack_reschedule": "https://example.com/ack_reschedule.wav",
        "ack_call_later": "https://example.com/ack_call_later.wav",
        "ack_stop": "https://example.com/ack_stop.wav",
        "ack_unclear": "https://example.com/ack_unclear.wav",
        "voicemail": "https://example.com/voicemail.wav",
        "goodbye": "https://example.com/goodbye.wav",
    }
    return CallContext(
        call_id=uuid.uuid4(),
        language="en",
        amd_result=amd_result,
        flow_state=flow_state,
        template=TemplateView(
            dtmf_map=dtmf_map,
            speech_enabled=speech_enabled,
            voicemail_policy=voicemail_policy,
        ),
        audio=audio,
        speech_threshold=speech_threshold,
    )


# ── Row 1: answered → human (no AMD) → greeting steps ────────────────────────

def test_answered_human_returns_greeting():
    ctx = make_ctx()
    decision = flow_next(ctx, Answered())
    assert not decision.finalize
    assert any(isinstance(s, Play) for s in decision.steps)
    assert any(isinstance(s, Gather) for s in decision.steps)


def test_answered_human_no_record_when_speech_disabled():
    ctx = make_ctx(speech_enabled=False)
    decision = flow_next(ctx, Answered())
    assert not any(isinstance(s, Record) for s in decision.steps)


def test_answered_human_includes_record_when_speech_enabled():
    ctx = make_ctx(speech_enabled=True)
    decision = flow_next(ctx, Answered())
    assert any(isinstance(s, Record) for s in decision.steps)


# ── Row 2: answered → AMD machine → voicemail branch ─────────────────────────

def test_answered_amd_machine_skip_and_retry():
    ctx = make_ctx(amd_result="machine", voicemail_policy="skip_and_retry")
    decision = flow_next(ctx, Answered())
    assert decision.finalize
    assert decision.outcome == "voicemail"
    assert len(decision.steps) == 1
    assert isinstance(decision.steps[0], Hangup)


def test_answered_amd_machine_leave_message():
    ctx = make_ctx(amd_result="machine", voicemail_policy="leave_message")
    decision = flow_next(ctx, Answered())
    assert decision.finalize
    assert decision.outcome == "voicemail"
    assert isinstance(decision.steps[0], Play)
    assert isinstance(decision.steps[1], Hangup)


def test_amd_result_event_machine_skip_and_retry():
    ctx = make_ctx(voicemail_policy="skip_and_retry")
    decision = flow_next(ctx, AmdResult(value="machine"))
    assert decision.finalize
    assert decision.outcome == "voicemail"


def test_amd_result_event_human_returns_greeting():
    ctx = make_ctx()
    decision = flow_next(ctx, AmdResult(value="human"))
    assert not decision.finalize
    assert any(isinstance(s, Play) for s in decision.steps)


# ── Row 3: DTMF digit in map → intent + ack + hangup ─────────────────────────

def test_dtmf_digit_1_confirm():
    ctx = make_ctx()
    decision = flow_next(ctx, Digits("1"))
    assert decision.finalize
    assert decision.intent is not None
    assert decision.intent.label == "confirm"
    assert decision.intent.confidence == 1.0
    assert decision.intent.source == "dtmf"
    assert decision.outcome == "confirmed"
    assert isinstance(decision.steps[-1], Hangup)


def test_dtmf_digit_2_decline():
    ctx = make_ctx()
    decision = flow_next(ctx, Digits("2"))
    assert decision.finalize
    assert decision.intent.label == "decline"
    assert decision.outcome == "declined"


def test_dtmf_digit_3_reschedule():
    ctx = make_ctx()
    decision = flow_next(ctx, Digits("3"))
    assert decision.finalize
    assert decision.intent.label == "reschedule"
    assert decision.outcome == "reschedule"


def test_dtmf_digit_9_stop_calling():
    ctx = make_ctx()
    decision = flow_next(ctx, Digits("9"))
    assert decision.finalize
    assert decision.intent.label == "stop_calling"
    assert decision.outcome == "opted_out"
    assert decision.opt_out is True


# ── Row 4: DTMF digit NOT in map → reprompt rule ─────────────────────────────

def test_dtmf_invalid_digit_first_reprompt():
    ctx = make_ctx(flow_state={"reprompts": 0})
    decision = flow_next(ctx, Digits("5"))
    assert not decision.finalize
    assert decision.new_flow_state["reprompts"] == 1
    assert any(isinstance(s, Play) for s in decision.steps)  # reprompt played
    assert any(isinstance(s, Gather) for s in decision.steps)


def test_dtmf_invalid_digit_second_reprompt_unclear():
    ctx = make_ctx(flow_state={"reprompts": 1})
    decision = flow_next(ctx, Digits("5"))
    assert decision.finalize
    assert decision.outcome == "unclear"


# ── Row 5: First digit of multi-digit input is used ──────────────────────────

def test_dtmf_multi_digit_uses_first():
    ctx = make_ctx()
    decision = flow_next(ctx, Digits("12"))
    assert decision.intent.label == "confirm"  # "1" maps to confirm


# ── Row 6: No input (timeout) → reprompt, then no_input ──────────────────────

def test_timeout_first_no_input_count():
    ctx = make_ctx(flow_state={"no_input_count": 0})
    decision = flow_next(ctx, Timeout())
    assert not decision.finalize
    assert decision.new_flow_state["no_input_count"] == 1


def test_timeout_second_finalizes_no_input():
    ctx = make_ctx(flow_state={"no_input_count": 1})
    decision = flow_next(ctx, Timeout())
    assert decision.finalize
    assert decision.outcome == "no_input"
    assert isinstance(decision.steps[-1], Hangup)


# ── Row 7: recording_ready → speech intent above threshold ────────────────────

def test_speech_result_above_threshold_confirm():
    ctx = make_ctx(speech_enabled=True, speech_threshold=0.6)
    speech = SpeechResult(text="yes I will come", intent="confirm", confidence=0.9)
    decision = flow_next(ctx, speech)
    assert decision.finalize
    assert decision.intent.label == "confirm"
    assert decision.outcome == "confirmed"


def test_speech_result_below_threshold_reprompts():
    ctx = make_ctx(speech_enabled=True, speech_threshold=0.6, flow_state={"reprompts": 0})
    speech = SpeechResult(text="hmm", intent="confirm", confidence=0.4)
    decision = flow_next(ctx, speech)
    assert not decision.finalize
    assert decision.new_flow_state["reprompts"] == 1


def test_speech_result_unclear_intent_reprompts():
    ctx = make_ctx(speech_enabled=True, speech_threshold=0.6, flow_state={"reprompts": 0})
    speech = SpeechResult(text="noise", intent="unclear", confidence=0.9)
    decision = flow_next(ctx, speech)
    assert not decision.finalize


def test_speech_result_stop_calling():
    ctx = make_ctx(speech_enabled=True, speech_threshold=0.6)
    speech = SpeechResult(text="stop calling me", intent="stop_calling", confidence=0.95)
    decision = flow_next(ctx, speech)
    assert decision.finalize
    assert decision.opt_out is True
    assert decision.outcome == "opted_out"


# ── Row 8: Completed before any intent → no_input ────────────────────────────

def test_completed_no_intent_captured():
    ctx = make_ctx()
    decision = flow_next(ctx, Completed(status="completed", duration=3))
    assert decision.finalize
    assert decision.outcome == "no_input"


# ── Row 9: Completed with no_answer / busy / failed ──────────────────────────

def test_completed_no_answer():
    ctx = make_ctx()
    decision = flow_next(ctx, Completed(status="no_answer", duration=0))
    assert decision.finalize
    assert decision.outcome == "no_answer"


def test_completed_busy():
    ctx = make_ctx()
    decision = flow_next(ctx, Completed(status="busy", duration=0))
    assert decision.finalize
    assert decision.outcome == "busy"


def test_completed_failed():
    ctx = make_ctx()
    decision = flow_next(ctx, Completed(status="failed", duration=0))
    assert decision.finalize
    assert decision.outcome == "failed"


def test_completed_canceled_maps_to_failed():
    ctx = make_ctx()
    decision = flow_next(ctx, Completed(status="canceled", duration=0))
    assert decision.finalize
    assert decision.outcome == "failed"


# ── Edge: digit pressed during the greeting (state fresh) ────────────────────

def test_digit_pressed_before_gather_fresh_state():
    """Digit arrives before any state is recorded — should still work."""
    ctx = make_ctx(flow_state={})
    decision = flow_next(ctx, Digits("1"))
    assert decision.finalize
    assert decision.intent.label == "confirm"


# ── Edge: duplicate Answered (already in_call) ────────────────────────────────

def test_duplicate_answered_is_idempotent():
    """Second Answered event produces greeting again (idempotency via DB)."""
    ctx = make_ctx(flow_state={"branch": "human"})
    d1 = flow_next(ctx, Answered())
    d2 = flow_next(ctx, Answered())
    assert not d1.finalize
    assert not d2.finalize


# ── Edge: Completed arrives before Answered ────────────────────────────────────

def test_completed_before_any_event():
    """Call provider sends completed with no_answer before Answered."""
    ctx = make_ctx()
    decision = flow_next(ctx, Completed(status="no_answer", duration=0))
    assert decision.finalize
    assert decision.outcome == "no_answer"


# ── Edge: RepromptRule exhaustion on second unclear speech ────────────────────

def test_speech_second_reprompt_exhaustion():
    ctx = make_ctx(speech_enabled=True, flow_state={"reprompts": 1}, speech_threshold=0.6)
    speech = SpeechResult(text="hmm", intent="confirm", confidence=0.2)
    decision = flow_next(ctx, speech)
    assert decision.finalize
    assert decision.outcome == "unclear"


# ── Voicemail: leave_message policy ──────────────────────────────────────────

def test_voicemail_leave_message_plays_voicemail_audio():
    ctx = make_ctx(voicemail_policy="leave_message")
    decision = flow_next(ctx, AmdResult(value="machine"))
    assert decision.finalize
    assert isinstance(decision.steps[0], Play)
    assert "voicemail" in decision.steps[0].audio_url


# ── Intent mapping completeness ───────────────────────────────────────────────

@pytest.mark.parametrize("digit,label,outcome,opt_out", [
    ("1", "confirm", "confirmed", False),
    ("2", "decline", "declined", False),
    ("3", "reschedule", "reschedule", False),
    ("9", "stop_calling", "opted_out", True),
])
def test_dtmf_intent_outcome_mapping(digit, label, outcome, opt_out):
    dtmf_map = {"1": "confirm", "2": "decline", "3": "reschedule", "9": "stop_calling"}
    ctx = make_ctx(dtmf_map=dtmf_map)
    decision = flow_next(ctx, Digits(digit))
    assert decision.intent.label == label
    assert decision.outcome == outcome
    assert decision.opt_out == opt_out
