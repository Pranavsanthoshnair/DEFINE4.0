# Veylo AI — Model Report

*Generated: 2026-10-09 | Service version: 0.2.0 | Member 3*

---

## 1. Models Used

| Model | Version | Provider | Purpose | Licence | Runs on |
|---|---|---|---|---|---|
| Sarvam Saaras | v4 | Sarvam AI API | Primary STT | Sarvam commercial ToS | Sarvam servers |
| Groq Whisper | whisper-large-v3-turbo | Groq API | Secondary STT / benchmark | OpenAI Whisper MIT | Groq servers |
| Sarvam Mayura | v1 | Sarvam AI API | Translation (en <-> Indic) | Sarvam commercial ToS | Sarvam servers |
| Sarvam Bulbul | v3 | Sarvam AI API | TTS (all demo languages) | Sarvam commercial ToS | Sarvam servers |
| Intent rules lexicon | — | Local | Primary intent classification | MIT (project code) | Our server |
| MuRIL intent ONNX | — | — | Fine-tuned intent model | **DEFERRED** — see section 3 | — |

> No model weights are downloaded or stored locally. The AI service makes
> API calls to Sarvam and Groq. The only local processing is deterministic
> intent rules and placeholder protection.

---

## 2. STT Benchmark

### Methodology

- **Test set:** 52 synthetic TTS-generated fixtures (4 languages x 4 labels x 3 phrases + silence)
- **Generation:** Sarvam Bulbul v3, voice `ritu` -> 8 kHz mono PCM16 WAV (Exotel phone profile)
- **Script:** `ai/generate_fixtures.py` + `ai/stt_benchmark.py`
- **Evaluation:** Both providers called concurrently on identical audio; latency measured wall-clock
- **Limitation:** Synthetic fixtures (TTS-generated, not real human speech). WER on real Exotel recordings not yet available. Replace fixtures with human recordings before final evaluation.

### Benchmark Results (synthetic fixtures, 2026-10-09)

| Provider | Model | Latency p50 | Latency p95 | Silence handling |
|---|---|---|---|---|
| **Sarvam** | Saaras v4 | ~750 ms | ~1200 ms | Correct (empty transcript) |
| **Groq** | Whisper Large v3 Turbo | ~720 ms | ~950 ms | Hallucinates ("Thank you.") |

### STT Provider Decision

`STT_PROVIDER=auto` (default) — races both providers, returns first result.

- **Indian language accuracy:** `STT_PROVIDER=sarvam` recommended — purpose-built for Indic phonology
- **Lowest latency:** `STT_PROVIDER=groq` — ~30 ms faster average
- **Silence handling:** Sarvam is safer without explicit VAD pre-filtering

**Recommended for demo:** `STT_PROVIDER=auto`

### Language Support

| Language | Code | Sarvam Saaras v4 | Groq Whisper | Demo priority |
|---|---|---|---|---|
| English | en-IN | Supported | Supported | Demo |
| Hindi | hi-IN | Supported | Supported | Demo |
| Malayalam | ml-IN | Supported | Supported | Demo |
| Tamil | ta-IN | Supported | Supported | Demo |
| Telugu | te-IN | Supported | Supported | Stretch |
| Kannada | kn-IN | Supported | Supported | Stretch |
| Bengali | bn-IN | Supported | Supported | Stretch |
| Marathi | mr-IN | Supported | Supported | Stretch |
| Gujarati | gu-IN | Supported | Supported | Stretch |

---

## 3. Intent Classification

### Architecture

```
Input text
    |
    v
[1] Rules engine (lexicon YAML — en, hi, ml, ta)
    |  confidence >= 0.9 -> return immediately
    |  confidence < 0.9 -> continue
    v
[2] LLM fallback (optional — LLM_FALLBACK=none by default)
    |  enabled: Groq or Gemini API call
    |  disabled: skip
    v
[3] Return "unclear" at confidence 0.0
```

### Lexicon Coverage

| Language | confirm | decline | reschedule | call_later | stop_calling |
|---|---|---|---|---|---|
| English | 10 phrases | 6 phrases | 4 phrases | 4 phrases | 5 phrases |
| Hindi | 12 phrases (Devanagari + Romanised) | 6 phrases | 4 phrases | 4 phrases | 5 phrases |
| Malayalam | 8 phrases (Script + Romanised) | 5 phrases | 3 phrases | 3 phrases | 3 phrases |
| Tamil | 8 phrases (Script + Romanised) | 5 phrases | 3 phrases | 3 phrases | 3 phrases |

### Decision Distribution (synthetic test)

| Stage | Share of utterances |
|---|---|
| Rules (confidence >= 0.9) | ~85% of clearly labelled utterances |
| Rules (ambiguous -> unclear) | ~10% |
| LLM fallback | 0% (disabled by default) |
| Returned as unclear | ~5% |

### Fine-tuned MuRIL ONNX Model — DEFERRED

**Decision:** MuRIL fine-tuning is deferred for the hackathon MVP per the spec:
*"If time is short: skip fine-tuning and ship rules plus LLM fallback."*
The rules-based pipeline handles all 4 demo languages reliably.

**Code is ready:** `ai/app/intent/model.py` has the ONNX inference skeleton.
`ai/ml/intent/` has stubbed scripts for data generation, training, and ONNX export.

**To fine-tune post-hackathon:**
1. Run `ai/ml/intent/generate_data.py` (uses Groq LLaMA for data generation)
2. Run `ai/ml/intent/train.py` on Colab GPU (MuRIL base, 4 epochs)
3. Run `ai/ml/intent/export_onnx.py` (dynamic int8 quantisation)
4. Copy `model.onnx` into the service; set `INTENT_MODEL_PATH`

**Target metrics:** macro F1 >= 0.90 on synthetic test, >= 0.80 on hand-written test.

---

## 4. Translation

### Provider

**Sarvam Mayura v1** — 23 Indic languages, formal mode

### Placeholder Protection

All `{key}` placeholders are replaced with numbered tokens (`[0]`, `[1]`, etc.)
before translation and restored after. Validation:
- All placeholder tokens present in translated output
- On failure: HTTP 422 `placeholder_lost` with missing keys listed

### Sample Outputs

| Source (English) | Target | Translation (illustrative) |
|---|---|---|
| "Hello {0}, join us on {1}" | Hindi | "नमस्ते {0}, {1} को हमारे साथ आइए" |
| "Please confirm your attendance" | Malayalam | "ദയവായി നിങ്ങളുടെ ഹാജർ സ്ഥിരീകരിക്കുക" |
| "The event is at {0}" | Tamil | "நிகழ்வு {0} இல் உள்ளது" |

*Actual output depends on Sarvam API at call time.*

---

## 5. Text-to-Speech

### Provider

**Sarvam Bulbul v3** — neural TTS, 8 kHz output for Exotel telephony

### Voices Used

| Language | Voice | Notes |
|---|---|---|
| English (en-IN) | `ritu` | Clear, professional |
| Hindi (hi-IN) | `ritu` | Natural calling voice |
| Malayalam (ml-IN) | `ritu` | Generic (ml-specific v3 voice TBD) |
| Tamil (ta-IN) | `ritu` | Generic (ta-specific v3 voice TBD) |

### Post-processing (`ai/app/tts/postprocess.py`)

1. Mono 8 kHz PCM16 WAV (Exotel format)
2. Loudness normalised to -16 LUFS (approximation)
3. Leading silence trimmed
4. 150 ms trailing silence appended

### Listening Test

Pending — to be conducted with a native speaker before first Exotel call.

---

## 6. End-to-End Latency

Measured on `STT_PROVIDER=auto`, 8 kHz WAV synthetic fixtures, LAN network.

| Stage | p50 | p95 |
|---|---|---|
| Audio decode | < 5 ms | < 10 ms |
| STT (Sarvam or Groq) | 720-750 ms | 950-1200 ms |
| Intent rules | < 5 ms | < 15 ms |
| **Total `/v1/speech-intent`** | **~730 ms** | **~1220 ms** |

**Spec target:** < 4 s for a 5 s utterance. **Met.**

---

## 7. Processing Location Facts (for PRIVACY.md)

| Component | Runs where | Data sent |
|---|---|---|
| STT — Sarvam Saaras v4 | Sarvam AI servers (India) | Audio bytes only |
| STT — Groq Whisper | Groq servers (US) | Audio bytes only |
| Translation — Sarvam Mayura v1 | Sarvam AI servers (India) | Template text only |
| TTS — Sarvam Bulbul v3 | Sarvam AI servers (India) | Rendered text only |
| Intent rules | Our server | Never leaves the process |
| LLM fallback | Groq/Google (if enabled) | Transcript text only — **off by default** |

**Privacy guarantees (LLM_FALLBACK=none):**
- Phone numbers: never sent to any external API
- Contact names: never sent to any external API
- Audio: sent to Sarvam/Groq for transcription only; not stored by us
- Transcripts: logged as length + language only; not logged verbatim

---

## 8. Limitations and Next Steps

### Current Limitations

1. Synthetic fixtures only — WER not measured on real phone call audio
2. MuRIL model deferred — intent is rules-only for hackathon
3. Groq hallucinates on silence — needs VAD pre-filter for production
4. Only `ritu` voice tested for ml-IN and ta-IN
5. LLM fallback inactive by default — ambiguous utterances return `unclear`

### Next Steps (post-hackathon)

1. Record real human audio fixtures (3 speakers per language, with consent)
2. Fine-tune MuRIL on Colab; export ONNX int8; load in service
3. Add silero-VAD pre-filter before Groq STT path
4. Enable LLM fallback for production intent quality
5. Evaluate language-specific Bulbul voices for Malayalam and Tamil
6. Load-test: 10 concurrent `/v1/speech-intent`, measure p95 + memory
