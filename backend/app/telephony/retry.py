"""
Retry and calling-window math.
Contract: CONTRACTS.md sections 9.4 and 9.5.
All functions are pure (no I/O) and fully unit-testable with fixed clocks.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

# ── Outcome sets (CONTRACTS.md section 3) ────────────────────────────────────

RETRYABLE_OUTCOMES = {
    "no_answer", "busy", "voicemail", "no_input", "unclear", "failed", "call_later"
}
NON_RESPONDER_SET = {"no_answer", "busy", "voicemail", "no_input"}
TERMINAL_OUTCOMES = {"confirmed", "declined", "reschedule", "opted_out"}

# ── Default retry policy ──────────────────────────────────────────────────────

DEFAULT_RETRY_POLICY: dict[str, int] = {
    "no_answer":  60,
    "busy":       30,
    "voicemail":  240,
    "failed":     15,
    "no_input":   120,
    "unclear":    1440,
    "call_later": 120,
}


# ── Window helpers ────────────────────────────────────────────────────────────

def in_window(
    now_utc: datetime,
    tz: str,
    start: time,
    end: time,
) -> bool:
    """
    Return True if the current local time is inside [start, end).

    Args:
        now_utc: Current UTC datetime (timezone-aware or naive treated as UTC).
        tz:      IANA timezone name, e.g. "Asia/Kolkata".
        start:   Window start time (local).
        end:     Window end time (local).
    """
    zone = ZoneInfo(tz)
    now_local = now_utc.astimezone(zone)
    local_time = now_local.time().replace(tzinfo=None)
    return start <= local_time < end


def next_window_start(
    now_utc: datetime,
    tz: str,
    start: time,
    end: time,
) -> datetime:
    """
    Return the next datetime (UTC) when the calling window opens.

    If we are currently inside the window, raises ValueError — callers should
    only call this when outside the window.
    """
    zone = ZoneInfo(tz)
    now_local = now_utc.astimezone(zone)

    # Candidate: today at window start
    candidate_local = now_local.replace(
        hour=start.hour,
        minute=start.minute,
        second=0,
        microsecond=0,
        tzinfo=None,
    )
    candidate = datetime(
        now_local.year, now_local.month, now_local.day,
        start.hour, start.minute, 0,
        tzinfo=zone,
    )

    # If today's window start has already passed, use tomorrow's
    if candidate <= now_local:
        candidate += timedelta(days=1)

    return candidate.astimezone(ZoneInfo("UTC"))


# ── Retry scheduling ──────────────────────────────────────────────────────────

def schedule_next_attempt(
    outcome: str,
    attempts: int,
    max_attempts: int,
    policy: dict[str, int],
    now_utc: datetime,
    tz: str,
    start: time,
    end: time,
) -> tuple[str, datetime | None, str | None]:
    """
    Compute the next state and attempt time for a contact after a call ends.

    Returns:
        (new_state, next_attempt_at, final_outcome)

    States: "waiting_retry" | "exhausted" | "done"
    """
    if outcome in TERMINAL_OUTCOMES:
        return ("done", None, outcome)

    if outcome not in RETRYABLE_OUTCOMES:
        # Treat unknown outcome as exhausted
        return ("exhausted", None, outcome)

    if attempts >= max_attempts:
        return ("exhausted", None, outcome)

    # Compute delay
    delay_minutes = policy.get(outcome, DEFAULT_RETRY_POLICY.get(outcome, 60))
    next_at = now_utc + timedelta(minutes=delay_minutes)

    # Clamp to calling window
    if not in_window(next_at, tz, start, end):
        next_at = next_window_start(next_at, tz, start, end)

    return ("waiting_retry", next_at, None)
