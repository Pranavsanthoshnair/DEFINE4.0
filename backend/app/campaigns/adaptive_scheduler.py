"""
Thompson Sampling Adaptive Campaign Retry Scheduler (Blueprint H1).

Learns optimal call-dispatch time slots across demographic segments using
a hierarchical Beta-Bernoulli bandit with empirical Bayes shrinkage.

Slots:
0: 09:00 - 11:00 (Early Morning)
1: 11:00 - 13:00 (Midday)
2: 13:00 - 15:00 (Early Afternoon)
3: 15:00 - 17:00 (Late Afternoon)
4: 17:00 - 19:00 (Early Evening)
5: 19:00 - 21:00 (Night Window)
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import List, Optional, Tuple, Dict, Any

from app.core.clock import Clock, get_clock

SLOT_HOURS: List[Tuple[int, int]] = [
    (9, 11),
    (11, 13),
    (13, 15),
    (15, 17),
    (17, 19),
    (19, 21),
]

SLOT_NAMES: List[str] = [
    "09:00-11:00 (Morning)",
    "11:00-13:00 (Midday)",
    "13:00-15:00 (Early Afternoon)",
    "15:00-17:00 (Late Afternoon)",
    "17:00-19:00 (Evening)",
    "19:00-21:00 (Night)",
]


@dataclass
class SlotCandidate:
    slot_idx: int
    slot_start: datetime
    days_until: int


@dataclass
class AdaptivePolicyConfig:
    m: float = 4.0               # Prior strength shrinkage to segment
    delta: float = 0.90          # Time-decay discount factor
    epsilon: float = 0.05        # Exploration probability
    min_gap_min: int = 60        # Minimum delay between consecutive attempts
    max_attempts_per_day: int = 2


def get_slot_idx_for_time(dt: datetime) -> int | None:
    """Determine the slot index (0..5) for a given UTC / local time."""
    hour = dt.hour
    for idx, (start_h, end_h) in enumerate(SLOT_HOURS):
        if start_h <= hour < end_h:
            return idx
    return None


def get_valid_future_slots(
    now: datetime,
    last_attempt_at: datetime | None = None,
    attempts_today: int = 0,
    max_lookahead_days: int = 4,
    policy: AdaptivePolicyConfig = AdaptivePolicyConfig(),
) -> List[SlotCandidate]:
    """Generate candidate future calling slots complying with calling-window and daily cap constraints."""
    candidates: List[SlotCandidate] = []
    min_allowed_time = now + timedelta(minutes=policy.min_gap_min) if last_attempt_at else now

    for day_offset in range(max_lookahead_days):
        target_date = (now + timedelta(days=day_offset)).date()
        
        # Check daily attempt cap for today
        if day_offset == 0 and attempts_today >= policy.max_attempts_per_day:
            continue

        for slot_idx, (start_h, _) in enumerate(SLOT_HOURS):
            slot_dt = datetime.combine(
                target_date,
                time(hour=start_h, minute=0, second=0),
                tzinfo=timezone.utc,
            )

            # Slot must be strictly in the future and satisfy min_gap
            if slot_dt >= min_allowed_time:
                candidates.append(
                    SlotCandidate(
                        slot_idx=slot_idx,
                        slot_start=slot_dt,
                        days_until=day_offset,
                    )
                )

    return candidates


def choose_adaptive_slot(
    segment: str,
    segment_stats: Dict[int, Tuple[int, int]], # slot_idx -> (successes, failures)
    contact_stats: Dict[int, Tuple[int, int]], # slot_idx -> (successes, failures)
    now: datetime,
    last_attempt_at: datetime | None = None,
    attempts_today: int = 0,
    policy: AdaptivePolicyConfig = AdaptivePolicyConfig(),
    rng: random.Random | None = None,
) -> Tuple[datetime | None, int | None, float | None, str]:
    """Select the optimal next attempt time slot using Thompson Sampling.

    Returns:
    --------
    (slot_start_datetime, slot_idx, sampled_theta, explainability_reason)
    """
    r = rng or random.Random()
    candidates = get_valid_future_slots(
        now=now,
        last_attempt_at=last_attempt_at,
        attempts_today=attempts_today,
        policy=policy,
    )

    if not candidates:
        return None, None, None, "No valid future slots within calling window horizon"

    # Epsilon-greedy exploration
    if r.random() < policy.epsilon:
        chosen = r.choice(candidates)
        reason = f"Exploration slot: {SLOT_NAMES[chosen.slot_idx]} (ε={policy.epsilon})"
        return chosen.slot_start, chosen.slot_idx, None, reason

    best_candidate: SlotCandidate | None = None
    best_score: float = -1.0
    best_theta: float = 0.0

    # Calculate segment means for shrinkage
    for cand in candidates:
        s_idx = cand.slot_idx
        seg_succ, seg_fail = segment_stats.get(s_idx, (0, 0))
        # Segment prior mean μ_seg
        seg_mu = (1.0 + seg_succ) / (2.0 + seg_succ + seg_fail)

        c_succ, c_fail = contact_stats.get(s_idx, (0, 0))
        # Shrinkage contact posterior: Beta(m*μ + s, m*(1-μ) + f)
        alpha = policy.m * seg_mu + c_succ
        beta_val = policy.m * (1.0 - seg_mu) + c_fail

        # Thompson sample theta
        theta = r.betavariate(max(0.01, alpha), max(0.01, beta_val))
        # Discounted score by lookahead days
        discounted_score = theta * (policy.delta ** cand.days_until)

        if discounted_score > best_score:
            best_score = discounted_score
            best_candidate = cand
            best_theta = theta

    if best_candidate is None:
        best_candidate = candidates[0]

    seg_succ, seg_fail = segment_stats.get(best_candidate.slot_idx, (0, 0))
    seg_pct = round(100.0 * (1.0 + seg_succ) / (2.0 + seg_succ + seg_fail), 1)
    reason = f"{SLOT_NAMES[best_candidate.slot_idx]}: segment '{segment}' pickup probability {seg_pct}% (sampled θ={best_theta:.2f})"

    return best_candidate.slot_start, best_candidate.slot_idx, round(best_theta, 4), reason
