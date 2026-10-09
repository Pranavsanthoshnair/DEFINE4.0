"""
Unit tests for retry and calling-window math.
Uses fixed clocks — no real time dependency.
"""

from __future__ import annotations

from datetime import datetime, time, timezone, timedelta

import pytest

from app.telephony.retry import (
    DEFAULT_RETRY_POLICY,
    RETRYABLE_OUTCOMES,
    TERMINAL_OUTCOMES,
    in_window,
    next_window_start,
    schedule_next_attempt,
)


# ── in_window ─────────────────────────────────────────────────────────────────

def _utc(h: int, m: int = 0) -> datetime:
    return datetime(2024, 10, 9, h, m, tzinfo=timezone.utc)


def _ist_utc(h: int, m: int = 0) -> datetime:
    """IST is UTC+5:30. To get IST hour h, UTC = h-5h30m."""
    return datetime(2024, 10, 9, h - 5, m - 30 if m >= 30 else m + 30, tzinfo=timezone.utc) \
        if m >= 30 else \
        datetime(2024, 10, 9, h - 6, m + 30, tzinfo=timezone.utc)


# Use actual UTC-based times for IST:
# IST 09:00 = UTC 03:30
# IST 21:00 = UTC 15:30
# IST 20:30 = UTC 15:00

@pytest.mark.parametrize("now_utc,expected", [
    (datetime(2024, 10, 9, 3, 30, tzinfo=timezone.utc), True),   # IST 09:00 — window opens
    (datetime(2024, 10, 9, 10, 0, tzinfo=timezone.utc), True),   # IST 15:30 — inside
    (datetime(2024, 10, 9, 15, 30, tzinfo=timezone.utc), False),  # IST 21:00 — window closes
    (datetime(2024, 10, 9, 1, 0, tzinfo=timezone.utc), False),   # IST 06:30 — before window
    (datetime(2024, 10, 9, 20, 0, tzinfo=timezone.utc), False),  # IST 01:30 next day — closed
])
def test_in_window_ist(now_utc, expected):
    result = in_window(now_utc, "Asia/Kolkata", time(9, 0), time(21, 0))
    assert result == expected


def test_in_window_dst_timezone():
    """Test with a timezone that observes DST (New York, UTC-4 in summer)."""
    # US/Eastern in summer = UTC-4. 10:00 ET = 14:00 UTC. Window 09:00-21:00 ET.
    now_utc = datetime(2024, 7, 15, 14, 0, tzinfo=timezone.utc)  # 10:00 ET
    assert in_window(now_utc, "America/New_York", time(9, 0), time(21, 0))

    # 23:00 ET = 03:00 UTC next day — outside window
    now_utc_outside = datetime(2024, 7, 15, 3, 0, tzinfo=timezone.utc)
    assert not in_window(now_utc_outside, "America/New_York", time(9, 0), time(21, 0))


# ── next_window_start ─────────────────────────────────────────────────────────

def test_next_window_start_after_window_closes():
    """IST 20:30 + 60 min = IST 21:30, outside window → next day 09:00 IST."""
    now_utc = datetime(2024, 10, 9, 15, 0, tzinfo=timezone.utc)  # IST 20:30
    # Already at/after window close (IST 21:00 = UTC 15:30), so next window start
    # is the next UTC moment in the window.
    next_at = now_utc + timedelta(minutes=60)  # IST 21:30 — outside window
    # next_window_start should give next day IST 09:00 = UTC 03:30
    nws = next_window_start(next_at, "Asia/Kolkata", time(9, 0), time(21, 0))
    nws_ist = nws.astimezone(__import__("zoneinfo").ZoneInfo("Asia/Kolkata"))
    assert nws_ist.hour == 9
    assert nws_ist.minute == 0


def test_next_window_start_dst():
    """Outside window in summer New York — next window start is next day 09:00 ET."""
    now_utc = datetime(2024, 7, 15, 3, 0, tzinfo=timezone.utc)  # 23:00 ET, closed
    nws = next_window_start(now_utc, "America/New_York", time(9, 0), time(21, 0))
    nws_et = nws.astimezone(__import__("zoneinfo").ZoneInfo("America/New_York"))
    assert nws_et.hour == 9
    assert nws_et.minute == 0


# ── schedule_next_attempt ─────────────────────────────────────────────────────

def test_terminal_outcome_returns_done():
    now = datetime(2024, 10, 9, 10, 0, tzinfo=timezone.utc)
    for outcome in TERMINAL_OUTCOMES:
        state, next_at, final = schedule_next_attempt(
            outcome, 1, 3, DEFAULT_RETRY_POLICY,
            now, "Asia/Kolkata", time(9, 0), time(21, 0),
        )
        assert state == "done"
        assert next_at is None
        assert final == outcome


def test_exhausted_when_attempts_reached():
    now = datetime(2024, 10, 9, 10, 0, tzinfo=timezone.utc)
    state, next_at, final = schedule_next_attempt(
        "no_answer", 3, 3, DEFAULT_RETRY_POLICY,
        now, "Asia/Kolkata", time(9, 0), time(21, 0),
    )
    assert state == "exhausted"
    assert next_at is None
    assert final == "no_answer"


def test_waiting_retry_inside_window():
    # Inside window: IST 10:00 = UTC 04:30
    now = datetime(2024, 10, 9, 4, 30, tzinfo=timezone.utc)
    state, next_at, final = schedule_next_attempt(
        "no_answer", 1, 3, DEFAULT_RETRY_POLICY,
        now, "Asia/Kolkata", time(9, 0), time(21, 0),
    )
    assert state == "waiting_retry"
    assert next_at is not None
    # next_at should be within the window (60 minutes later)
    assert in_window(next_at, "Asia/Kolkata", time(9, 0), time(21, 0))


def test_retry_clamps_to_next_window_when_outside():
    """IST 20:30 + 60 min delay = IST 21:30 (outside window) → clamp to next day 09:00."""
    now = datetime(2024, 10, 9, 15, 0, tzinfo=timezone.utc)  # IST 20:30
    state, next_at, final = schedule_next_attempt(
        "no_answer", 1, 3, {"no_answer": 60},
        now, "Asia/Kolkata", time(9, 0), time(21, 0),
    )
    assert state == "waiting_retry"
    assert next_at is not None
    from zoneinfo import ZoneInfo
    next_ist = next_at.astimezone(ZoneInfo("Asia/Kolkata"))
    assert next_ist.hour == 9
    assert next_ist.minute == 0


def test_call_later_policy():
    now = datetime(2024, 10, 9, 4, 30, tzinfo=timezone.utc)  # IST 10:00
    state, next_at, _ = schedule_next_attempt(
        "call_later", 1, 3, DEFAULT_RETRY_POLICY,
        now, "Asia/Kolkata", time(9, 0), time(21, 0),
    )
    assert state == "waiting_retry"
    expected_delay = timedelta(minutes=DEFAULT_RETRY_POLICY["call_later"])
    # Allow 10 seconds slop
    assert abs((next_at - now) - expected_delay).total_seconds() < 10


def test_unknown_outcome_exhausted():
    now = datetime(2024, 10, 9, 10, 0, tzinfo=timezone.utc)
    state, _, _ = schedule_next_attempt(
        "some_unknown_outcome", 1, 3, DEFAULT_RETRY_POLICY,
        now, "Asia/Kolkata", time(9, 0), time(21, 0),
    )
    assert state == "exhausted"
