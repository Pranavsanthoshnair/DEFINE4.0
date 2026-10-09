"""
Pure flow engine: next(call_ctx, event) -> FlowDecision.

This function performs NO I/O.  It only reads the context and event and
returns a decision.  The caller (webhook handler) is responsible for all
side-effects: DB writes, AI calls, HTTP responses.

State machine rows from CONTRACTS.md section 9.2 are implemented below.
"""

from __future__ import annotations

import copy

from app.telephony.flow.context import (
    Answered,
    AmdResult,
    CallContext,
    Completed,
    Digits,
    FlowDecision,
    FlowEvent,
    IntentResult,
    RecordingReady,
    SpeechResult,
    Timeout,
)
from app.telephony.providers.base import Gather, Hangup, Play, Record

# ── Outcome constants (from CONTRACTS.md section 3) ──────────────────────────

TERMINAL_OUTCOMES = {"confirmed", "declined", "reschedule", "opted_out"}

# Intent → outcome mapping
INTENT_TO_OUTCOME: dict[str, str] = {
    "confirm": "confirmed",
    "decline": "declined",
    "reschedule": "reschedule",
    "call_later": "call_later",
    "stop_calling": "opted_out",
    "unclear": "unclear",
}

# ── Default flow state ────────────────────────────────────────────────────────

def _default_flow_state() -> dict:
    return {
        "reprompts": 0,
        "no_input_count": 0,
        "speech_attempts": 0,
        "branch": "human",
    }


def _merge_state(existing: dict) -> dict:
    """Ensure all expected keys are present (handles legacy partial states)."""
    defaults = _default_flow_state()
    defaults.update(existing)
    return defaults


# ── Helpers ───────────────────────────────────────────────────────────────────

def _greeting_steps(ctx: CallContext) -> list:
    """[Play(greeting), Gather(prompt)] plus optional Record if speech_enabled."""
    steps: list = [
        Play(audio_url=ctx.audio.get("greeting", "")),
        Gather(
            prompt_audio_url=ctx.audio.get("prompt", ""),
            max_digits=1,
            timeout_sec=6,
        ),
    ]
    if ctx.template.speech_enabled:
        steps.append(Record(max_seconds=6, silence_timeout_sec=2, play_beep=True))
    return steps


def _reprompt_steps(ctx: CallContext) -> list:
    """[Play(reprompt), Gather(prompt)]."""
    return [
        Play(audio_url=ctx.audio.get("reprompt", "")),
        Gather(
            prompt_audio_url=ctx.audio.get("prompt", ""),
            max_digits=1,
            timeout_sec=6,
        ),
    ]


def _ack_and_hangup(ctx: CallContext, intent_label: str) -> list:
    """Play the correct acknowledgement segment then hang up."""
    ack_key = {
        "confirm": "ack_confirm",
        "decline": "ack_decline",
        "reschedule": "ack_reschedule",
        "call_later": "ack_call_later",
        "stop_calling": "ack_stop",
        "unclear": "ack_unclear",
    }.get(intent_label, "goodbye")
    return [Play(audio_url=ctx.audio.get(ack_key, "")), Hangup()]


def _finalize_with_intent(
    ctx: CallContext,
    state: dict,
    intent_label: str,
    confidence: float,
    source: str,
    raw_input: str,
    stt_model: str | None = None,
    latency_ms: int | None = None,
) -> FlowDecision:
    """Helper for building a finalizing decision from an intent."""
    opt_out = intent_label == "stop_calling"
    outcome = INTENT_TO_OUTCOME.get(intent_label, "unclear")
    intent = IntentResult(
        label=intent_label,
        confidence=confidence,
        source=source,
        raw_input=raw_input,
        stt_model=stt_model,
        latency_ms=latency_ms,
    )
    return FlowDecision(
        steps=_ack_and_hangup(ctx, intent_label),
        intent=intent,
        outcome=outcome,
        finalize=True,
        new_flow_state=state,
        opt_out=opt_out,
    )


# ── Main entry point ──────────────────────────────────────────────────────────

def next(call_ctx: CallContext, event: FlowEvent) -> FlowDecision:  # noqa: A001
    """
    Pure state-machine step function.
    Returns a FlowDecision; performs no I/O.
    """
    ctx = call_ctx
    state = _merge_state(copy.deepcopy(ctx.flow_state))

    # ── Answered ─────────────────────────────────────────────────────────────
    if isinstance(event, Answered):
        # If we already know this is a machine (from a prior AmdResult event
        # processed in-sequence), delegate; otherwise treat as human.
        if ctx.amd_result == "machine":
            return _handle_voicemail(ctx, state)
        # Mark branch and return greeting
        state["branch"] = "human"
        return FlowDecision(
            steps=_greeting_steps(ctx),
            new_flow_state=state,
        )

    # ── AmdResult ─────────────────────────────────────────────────────────────
    if isinstance(event, AmdResult):
        if event.value == "machine":
            state["branch"] = "voicemail"
            return _handle_voicemail(ctx, state)
        # Human confirmed
        state["branch"] = "human"
        return FlowDecision(
            steps=_greeting_steps(ctx),
            new_flow_state=state,
        )

    # ── DTMF Digits ──────────────────────────────────────────────────────────
    if isinstance(event, Digits):
        # Use only the first digit
        digit = event.value[0] if event.value else ""
        dtmf_map = ctx.template.dtmf_map

        if digit in dtmf_map:
            intent_label = dtmf_map[digit]
            return _finalize_with_intent(
                ctx, state,
                intent_label=intent_label,
                confidence=1.0,
                source="dtmf",
                raw_input=digit,
            )
        else:
            # Digit not in map → treat as unclear input → reprompt rule
            return _apply_reprompt_rule(ctx, state)

    # ── Timeout (no input) ────────────────────────────────────────────────────
    if isinstance(event, Timeout):
        no_input = state.get("no_input_count", 0)
        if no_input == 0:
            state["no_input_count"] = 1
            return FlowDecision(
                steps=_reprompt_steps(ctx),
                new_flow_state=state,
            )
        else:
            # Second silence → finalize no_input
            return FlowDecision(
                steps=[Play(audio_url=ctx.audio.get("goodbye", "")), Hangup()],
                outcome="no_input",
                finalize=True,
                new_flow_state=state,
            )

    # ── RecordingReady (speech path) ──────────────────────────────────────────
    if isinstance(event, RecordingReady):
        # The webhook handler already called AI and fed us a SpeechResult;
        # but if a raw RecordingReady arrives here it means we need to
        # trigger the AI call (async path).  The engine itself cannot do I/O,
        # so we return a sentinel decision with no steps and no outcome,
        # which the webhook handler interprets as "call AI then re-enter engine
        # with SpeechResult".  This is the async speech path.
        return FlowDecision(
            steps=[],
            new_flow_state=state,
        )

    # ── SpeechResult ──────────────────────────────────────────────────────────
    if isinstance(event, SpeechResult):
        if not ctx.template.speech_enabled:
            return _apply_reprompt_rule(ctx, state)

        intent_label = event.intent
        confidence = event.confidence
        threshold = ctx.speech_threshold

        if confidence >= threshold and intent_label != "unclear":
            return _finalize_with_intent(
                ctx, state,
                intent_label=intent_label,
                confidence=confidence,
                source="speech",
                raw_input=event.text,
                stt_model=event.stt_model,
                latency_ms=event.latency_ms,
            )
        else:
            # Low confidence / unclear → reprompt rule
            state["speech_attempts"] = state.get("speech_attempts", 0) + 1
            return _apply_reprompt_rule(ctx, state)

    # ── Completed ─────────────────────────────────────────────────────────────
    if isinstance(event, Completed):
        status = event.status.lower()

        # Completed without any intent being captured
        if status == "completed":
            # If no outcome was set before, it means caller hung up mid-call
            return FlowDecision(
                steps=[],
                outcome="no_input",
                finalize=True,
                new_flow_state=state,
            )

        # Mapping non-answer statuses to outcomes
        outcome_map = {
            "no_answer": "no_answer",
            "busy": "busy",
            "failed": "failed",
            "canceled": "failed",
        }
        outcome = outcome_map.get(status, "failed")
        return FlowDecision(
            steps=[],
            outcome=outcome,
            finalize=True,
            new_flow_state=state,
        )

    # Fallback: unknown event type
    return FlowDecision(steps=[], new_flow_state=state)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _handle_voicemail(ctx: CallContext, state: dict) -> FlowDecision:
    """Handle the voicemail branch per template policy (CONTRACTS.md 9.3)."""
    policy = ctx.template.voicemail_policy
    state["branch"] = "voicemail"
    if policy == "leave_message":
        return FlowDecision(
            steps=[Play(audio_url=ctx.audio.get("voicemail", "")), Hangup()],
            outcome="voicemail",
            finalize=True,
            new_flow_state=state,
        )
    else:  # skip_and_retry
        return FlowDecision(
            steps=[Hangup()],
            outcome="voicemail",
            finalize=True,
            new_flow_state=state,
        )


def _apply_reprompt_rule(ctx: CallContext, state: dict) -> FlowDecision:
    """
    Reprompt rule (CONTRACTS.md 9.2):
    - reprompts == 0 → play reprompt, Gather again
    - reprompts >= 1 → outcome unclear, play ack_unclear, hangup
    """
    reprompts = state.get("reprompts", 0)
    if reprompts == 0:
        state["reprompts"] = 1
        return FlowDecision(
            steps=_reprompt_steps(ctx),
            new_flow_state=state,
        )
    else:
        return FlowDecision(
            steps=[Play(audio_url=ctx.audio.get("ack_unclear", "")), Hangup()],
            outcome="unclear",
            finalize=True,
            new_flow_state=state,
        )
