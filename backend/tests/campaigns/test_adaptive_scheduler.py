"""
Unit tests for Thompson Sampling Adaptive Scheduler (Blueprint H1).
"""

import random
from datetime import datetime, timezone, timedelta
from app.campaigns.adaptive_scheduler import (
    choose_adaptive_slot,
    get_valid_future_slots,
    AdaptivePolicyConfig,
    SLOT_NAMES,
)


def test_adaptive_slot_deterministic_with_seed():
    now = datetime(2026, 10, 10, 10, 0, 0, tzinfo=timezone.utc)
    segment_stats = {
        0: (2, 8),   # 09-11: 20%
        1: (3, 7),   # 11-13: 30%
        4: (18, 2),  # 17-19: 90% (Evening high-probability)
        5: (15, 5),  # 19-21: 75%
    }
    contact_stats = {}

    rng1 = random.Random(42)
    slot1, idx1, theta1, reason1 = choose_adaptive_slot(
        segment="students",
        segment_stats=segment_stats,
        contact_stats=contact_stats,
        now=now,
        rng=rng1,
    )

    rng2 = random.Random(42)
    slot2, idx2, theta2, reason2 = choose_adaptive_slot(
        segment="students",
        segment_stats=segment_stats,
        contact_stats=contact_stats,
        now=now,
        rng=rng2,
    )

    assert slot1 == slot2
    assert idx1 == idx2 in (4, 5)  # Should choose evening/night slots 4 or 5
    assert theta1 == theta2
    assert "students" in reason1
    assert "personal" not in reason1.lower()


def test_adaptive_slot_respects_min_gap_constraint():
    now = datetime(2026, 10, 10, 9, 30, 0, tzinfo=timezone.utc)
    last_attempt = datetime(2026, 10, 10, 9, 30, 0, tzinfo=timezone.utc)
    policy = AdaptivePolicyConfig(min_gap_min=60) # 1 hour minimum gap

    candidates = get_valid_future_slots(now=now, last_attempt_at=last_attempt, policy=policy)
    # Today's 09:00 slot starts before min_allowed_time (10:30), so 09:00 today should not be a candidate
    todays_morning = [c for c in candidates if c.days_until == 0 and c.slot_idx == 0]
    assert len(todays_morning) == 0


def test_adaptive_slot_respects_daily_cap():
    now = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)
    policy = AdaptivePolicyConfig(max_attempts_per_day=2)

    # 2 attempts already today -> should only return tomorrow and beyond
    candidates = get_valid_future_slots(now=now, attempts_today=2, policy=policy)
    assert all(c.days_until >= 1 for c in candidates)
