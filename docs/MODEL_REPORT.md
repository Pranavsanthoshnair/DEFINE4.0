# Model Report

**Veylo · DEFINE 4.0 · PR 002**

## Models Used

| Model | Version | Purpose | Licence | Hosted |
|---|---|---|---|---|
| ElevenLabs TTS | `eleven_multilingual_v2` | Pre-render voice audio for all languages | Commercial API | ElevenLabs cloud |
| Faster-Whisper | small | Speech-to-text on phone audio | MIT | Self-hosted on Render |
| Intent classifier | Rule-based + keyword | Map STT text to intent labels | N/A (internal) | Self-hosted |
| IndicTrans2 (optional) | — | Translation EN→HI/ML/TA | MIT | Self-hosted (not active in v1) |

## Speech-to-Text Performance

> Measurements on phone-quality audio (8 kHz, G.711 μ-law) — TBD pending Exotel testing.

| Language | WER estimate | Source |
|---|---|---|
| English (Indian accent) | ~18% | Literature (Faster-Whisper small) |
| Hindi | ~22% | Literature |
| Malayalam | ~35% | Literature (limited training data) |
| Tamil | ~30% | Literature |

**Note:** WER on narrow-band telephony is higher than published benchmarks on clean audio. Actual measurements to be recorded after live call testing.

## Intent Classification

| Intent | Method | Precision (estimated) | Recall (estimated) |
|---|---|---|---|
| confirm (1 / "yes" / "attending") | DTMF + keyword | >0.99 (DTMF) | >0.99 |
| decline (2 / "no" / "can't") | DTMF + keyword | >0.99 (DTMF) | >0.99 |
| call_later (3 / "callback") | DTMF + keyword | >0.99 (DTMF) | >0.99 |
| stop_calling (9) | DTMF only | >0.99 | >0.99 |
| unclear | Fallback when confidence < τ | — | — |

**Confidence threshold τ:** 0.6 (default). Payment use case: DTMF only, speech path disabled.

## Adaptive Scheduler (H1)

Algorithm: Thompson sampling with hierarchical Beta-Bernoulli model.

Parameters:
- `prior_strength m = 4`
- `discount δ = 0.9` per slot distance
- `exploration ε = 0.05`
- 6 two-hour slots: 09-11, 11-13, 13-15, 15-17, 17-19, 19-21

**Simulation results (20 seeds, 150 contacts):**

| Population | Adaptive answer rate | Fixed answer rate | Seeds where adaptive wins |
|---|---|---|---|
| Structured (time-of-day pattern) | TBD — run `/api/v1/simulation/run` | TBD | TBD / 20 |
| Control (flat, H19) | TBD | TBD | TBD / 20 (expected ~10/20, no gain) |

> Fill in after running the simulation endpoint. These are populated live from the API.

**Honest limit:** The improvement is demonstrated on a synthetic population. Real call data is needed to validate on actual pickup patterns. The algorithm is real; the numbers are simulated.

## TTS Quality

ElevenLabs `eleven_multilingual_v2` with voice `EXAVITQu4vr4xnSDxMaL` (Sarah).

- Native speaker check: TBD — to be completed before demo for Hindi and one Dravidian language.
- Date/number rendering: delegated to pre-written scripts with numbers spelled out, not passed as digits to TTS.

## End-to-End Latency

| Stage | p50 (estimate) | p95 (estimate) | Notes |
|---|---|---|---|
| Dial to ring | ~2 s | ~4 s | Exotel network |
| Ring to answer | ~5–15 s | ~25 s | Contact dependent |
| Audio play (pre-rendered) | ~0 ms | ~0 ms | Served from cache |
| DTMF capture | ~1 s | ~3 s | After tone |
| Webhook to intent | ~200 ms | ~500 ms | Supabase round-trip |
| Total (answered + DTMF) | ~8 s | ~20 s | — |

> All figures are estimates. Measure on live Exotel calls and update before demo.
