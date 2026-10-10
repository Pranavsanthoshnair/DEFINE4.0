# Calling Approach

**Veylo · DEFINE 4.0 · PR 002**

## Three Approaches Compared

| Approach | Cost per call | In-call latency | Failure modes | Our choice |
|---|---|---|---|---|
| **Scripted keypad only** | Low | ~0 ms (pre-recorded) | Miskey, no response | For payment reminders |
| **Conversational voice agent** | High (LLM per turn) | 800–2000 ms (streaming) | Mishears, hangs, high-stakes misread | Too risky for structured RSVP |
| **Hybrid: recorded prompt + keypad + speech** | Medium | ~0 ms prompt + 400 ms STT | Confidence gate handles unclear | ✅ **Our choice** |

> Latency figures are p50 estimates. Actual measurements: TBD (measure on Exotel during testing).

## Why Hybrid

Narrow-band phone audio (8 kHz, G.711) degrades speech recognition. A conversational agent risks misreading high-stakes replies (clinic: patient assumed attending; payment: wrong amount). We pre-render all audio with ElevenLabs, so the voice is consistent and the latency is zero at call time.

Speech is enabled for seminar and clinic use cases with a confidence threshold. Payment calls are keypad-only. Intent below threshold → one re-prompt emphasising the keypad → outcome `unclear`. Never a silent failure.

## Call Flow

```
Dial contact
    │
    ├─ No answer / busy → retry with adaptive scheduler (H1)
    │
    └─ Answered
           │
           ├─ AMD: machine detected → voicemail policy (leave message or hang up)
           │
           └─ Human
                  │
                  Play greeting (ElevenLabs, pre-rendered, language-matched)
                  │
                  Wait for DTMF or speech
                  │
                  ├─ DTMF received → map to intent → play acknowledgement → hang up
                  │
                  ├─ Speech (if enabled) → STT → intent classification
                  │      ├─ confidence ≥ τ → intent → play acknowledgement → hang up
                  │      └─ confidence < τ → re-prompt (keypad emphasis) → DTMF fallback
                  │
                  ├─ Timeout → re-prompt → timeout again → outcome: no_input
                  │
                  └─ Key 9 → opt out → suppress → hang up
                     Key 0 → repeat message
                     Key 8 → switch language → replay in chosen language
```

## Graceful Degradation Chain (H15)

1. Speech layer unavailable → circuit breaker switches to keypad-only; calls continue
2. Audio asset missing for language → fall back to cached English audio, noted in call_events
3. Webhook retry on crash → idempotent handlers, 15-minute sweeper
4. Every unrecoverable path ends as `failed` with a reason, never an unexplained gap

## Voicemail Policy per Use Case (H12)

| Use case | Policy |
|---|---|
| seminar | Leave short message: event name, callback number |
| clinic | Leave message: appointment confirmation request only |
| school | Leave short message |
| payment | Leave no detail — callback notice only |

Voicemail is **never counted as a human response** and counts as a failure for H1 learning.

## Cost and Latency Table

| Operation | p50 | p95 | Cost estimate |
|---|---|---|---|
| ElevenLabs TTS (per segment, pre-rendered) | ~2 s | ~5 s | ~$0.003/segment |
| Exotel outbound call | ~2 s ring | — | ~₹0.60/min (TBD) |
| Speech-to-text (Whisper, phone audio) | ~400 ms | ~900 ms | self-hosted |
| Intent classification | ~50 ms | ~200 ms | self-hosted |
| End-to-end (dial to intent) | ~8 s | ~15 s | — |

> All measurements marked TBD are to be filled after Exotel testing. Numbers above are estimates.
