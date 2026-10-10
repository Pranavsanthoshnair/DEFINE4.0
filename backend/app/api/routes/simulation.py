"""
H1 + H19 — Simulation endpoint.

Runs a synthetic population through fixed vs adaptive scheduling policies
using a simulated clock. Results are LABELLED SIMULATED on every response.

GET /api/v1/simulation/run?seeds=20&contacts=200
"""
from __future__ import annotations

import random
import math
from typing import List, Dict, Any

from fastapi import APIRouter, Query

router = APIRouter()

# ── Population definition ─────────────────────────────────────────────────────

_SEGMENTS = {
    "students":  [0.10, 0.12, 0.15, 0.20, 0.38, 0.45],   # peak evenings
    "faculty":   [0.18, 0.40, 0.38, 0.30, 0.18, 0.12],   # peak midday
    "parents":   [0.12, 0.15, 0.20, 0.38, 0.35, 0.20],   # peak late afternoon
}

_CONTROL_SEGMENTS = {
    "students":  [0.22, 0.22, 0.22, 0.22, 0.22, 0.22],   # flat — H19 negative control
    "faculty":   [0.22, 0.22, 0.22, 0.22, 0.22, 0.22],
    "parents":   [0.22, 0.22, 0.22, 0.22, 0.22, 0.22],
}

_SLOT_LABELS = ["09-11", "11-13", "13-15", "15-17", "17-19", "19-21"]
_MAX_ATTEMPTS = 4


def _jitter(base: float, rng: random.Random, spread: float = 0.08) -> float:
    return max(0.01, min(0.99, base + rng.uniform(-spread, spread)))


def _make_population(n: int, segments: Dict, rng: random.Random) -> List[Dict]:
    seg_names = list(segments.keys())
    contacts = []
    for i in range(n):
        seg = seg_names[i % len(seg_names)]
        pickup_probs = [_jitter(p, rng) for p in segments[seg]]
        contacts.append({"id": i, "segment": seg, "pickup_probs": pickup_probs,
                         "attempts": 0, "answered": False,
                         "successes": [0]*6, "failures": [0]*6})
    return contacts


# ── Fixed policy ──────────────────────────────────────────────────────────────

def _fixed_slot(_contact: Dict, _rng: random.Random) -> int:
    """Always pick slot 2 (13-15) — the PRD default midday retry."""
    return 2


# ── Adaptive policy (Thompson sampling) ──────────────────────────────────────

def _adaptive_slot(contact: Dict, seg_stats: Dict, rng: random.Random) -> int:
    best_slot, best_score = 0, -1.0
    for s in range(6):
        seg = contact["segment"]
        seg_mu = (seg_stats[seg]["successes"][s] + 1) / (
            seg_stats[seg]["successes"][s] + seg_stats[seg]["failures"][s] + 2
        )
        a = 4 * seg_mu + contact["successes"][s]
        b = 4 * (1 - seg_mu) + contact["failures"][s]
        theta = rng.betavariate(max(0.01, a), max(0.01, b))
        decay = 0.9 ** (s / 2)
        score = theta * decay
        if score > best_score:
            best_score, best_slot = score, s
    # ε-greedy exploration
    if rng.random() < 0.05:
        best_slot = rng.randint(0, 5)
    return best_slot


def _run_simulation(n_contacts: int, n_rounds: int, segments: Dict, seed: int, adaptive: bool) -> Dict:
    rng = random.Random(seed)
    contacts = _make_population(n_contacts, segments, rng)
    seg_stats = {seg: {"successes": [0]*6, "failures": [0]*6} for seg in segments}

    rounds_data = []
    for round_no in range(1, n_rounds + 1):
        pickups = 0
        attempts = 0
        for contact in contacts:
            if contact["answered"] or contact["attempts"] >= _MAX_ATTEMPTS:
                continue
            slot = _adaptive_slot(contact, seg_stats, rng) if adaptive else _fixed_slot(contact, rng)
            pickup = rng.random() < contact["pickup_probs"][slot]
            contact["attempts"] += 1
            attempts += 1
            if pickup:
                contact["answered"] = True
                contact["successes"][slot] += 1
                seg_stats[contact["segment"]]["successes"][slot] += 1
                pickups += 1
            else:
                contact["failures"][slot] += 1
                seg_stats[contact["segment"]]["failures"][slot] += 1
        rate = round(pickups / attempts, 3) if attempts > 0 else 0
        rounds_data.append({"round": round_no, "pickups": pickups,
                             "attempts": attempts, "pickup_rate": rate})

    total_answered = sum(1 for c in contacts if c["answered"])
    wasted = sum(c["attempts"] for c in contacts if not c["answered"])
    return {
        "rounds": rounds_data,
        "total_answered": total_answered,
        "total_contacts": n_contacts,
        "wasted_attempts": wasted,
        "answer_rate": round(total_answered / n_contacts, 3),
    }


def _aggregate_seeds(runs: List[Dict]) -> List[Dict]:
    n_rounds = len(runs[0]["rounds"])
    result = []
    for r in range(n_rounds):
        rates = [run["rounds"][r]["pickup_rate"] for run in runs]
        mean = sum(rates) / len(rates)
        std = math.sqrt(sum((x - mean) ** 2 for x in rates) / len(rates))
        ci = 1.96 * std / math.sqrt(len(rates))
        result.append({
            "round": r + 1,
            "pickup_rate_mean": round(mean, 3),
            "pickup_rate_ci": round(ci, 3),
        })
    return result


@router.get("/run")
async def run_simulation(
    seeds: int = Query(20, ge=1, le=50),
    contacts: int = Query(150, ge=30, le=500),
    rounds: int = Query(4, ge=2, le=6),
):
    """
    H1 + H19: Run fixed vs adaptive simulation on structured AND control populations.
    All results are SIMULATED — labelled on every response.
    """
    adaptive_runs, fixed_runs = [], []
    ctrl_adaptive_runs, ctrl_fixed_runs = [], []

    for seed in range(seeds):
        adaptive_runs.append(_run_simulation(contacts, rounds, _SEGMENTS, seed, True))
        fixed_runs.append(_run_simulation(contacts, rounds, _SEGMENTS, seed, False))
        ctrl_adaptive_runs.append(_run_simulation(contacts, rounds, _CONTROL_SEGMENTS, seed, True))
        ctrl_fixed_runs.append(_run_simulation(contacts, rounds, _CONTROL_SEGMENTS, seed, False))

    adaptive_better = sum(
        1 for a, f in zip(adaptive_runs, fixed_runs)
        if a["answer_rate"] > f["answer_rate"]
    )
    ctrl_adaptive_better = sum(
        1 for a, f in zip(ctrl_adaptive_runs, ctrl_fixed_runs)
        if a["answer_rate"] > f["answer_rate"]
    )

    return {
        "DISCLAIMER": "ALL RESULTS ARE SIMULATED. Synthetic population, no real call data.",
        "parameters": {"seeds": seeds, "contacts_per_seed": contacts,
                       "rounds": rounds, "segments": list(_SEGMENTS.keys())},
        "structured_population": {
            "description": "Students peak evenings, faculty peak midday, parents late afternoon.",
            "adaptive": _aggregate_seeds(adaptive_runs),
            "fixed": _aggregate_seeds(fixed_runs),
            "adaptive_better_in_seeds": adaptive_better,
            "total_seeds": seeds,
            "avg_answer_rate_adaptive": round(sum(r["answer_rate"] for r in adaptive_runs) / seeds, 3),
            "avg_answer_rate_fixed": round(sum(r["answer_rate"] for r in fixed_runs) / seeds, 3),
        },
        "control_population": {
            "description": "H19 NEGATIVE CONTROL — flat pickup probability, no time-of-day pattern.",
            "adaptive": _aggregate_seeds(ctrl_adaptive_runs),
            "fixed": _aggregate_seeds(ctrl_fixed_runs),
            "adaptive_better_in_seeds": ctrl_adaptive_better,
            "total_seeds": seeds,
            "note": "Adaptive should show NO meaningful gain here — proving the improvement is real, not rigged.",
            "avg_answer_rate_adaptive": round(sum(r["answer_rate"] for r in ctrl_adaptive_runs) / seeds, 3),
            "avg_answer_rate_fixed": round(sum(r["answer_rate"] for r in ctrl_fixed_runs) / seeds, 3),
        },
    }
