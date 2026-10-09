# Member 3 — AI and Language Layer

**You own:** the AI service (speech to text, intent classification, translation, text to speech), the intent dataset and the fine-tuned model, the STT benchmark, the audio fixtures, and the model report.

**Read first:** `PRD.md` and `CONTRACTS.md` (section 7 is your API contract and must be implemented exactly; sections 5 and 11 also matter).

**If you are using an AI coding agent:** give it this file plus `CONTRACTS.md`. Endpoint paths, request fields, response fields and error codes are fixed. Model repository names below are from memory: before using any of them, verify the exact name and licence on Hugging Face and record the verified name in `services/ai/models.yaml`.

---

## 1. What you deliver

1. AI service `services/ai` exposing the endpoints in contract section 7, stateless, CPU friendly, Docker image.
2. Stub mode (canned responses) in the first hours so other members are never blocked.
3. STT benchmark and a chosen STT model per language.
4. Rules layer plus fine-tuned MuRIL intent model (ONNX int8) plus LLM fallback.
5. Translation with IndicTrans2 and placeholder protection.
6. TTS pre-render with edge-tts (default) and optional Indic Parler-TTS.
7. Audio fixtures (`fixtures/audio/`) recorded on real phone-quality audio.
8. `docs/MODEL_REPORT.md` with WER per model and language, intent F1 per language, latency, and the processing-location facts.

## 2. Directory ownership

```
services/ai/
  Dockerfile, pyproject.toml, models.yaml
  app/
    main.py                  # FastAPI, auth dependency, /healthz
    config.py
    audio/{io.py, resample.py, vad.py}
    stt/{base.py, faster_whisper_engine.py, indic_conformer_engine.py, groq_engine.py, router.py}
    intent/{rules.py, model.py, llm_fallback.py, pipeline.py, lexicon/{en,hi,ml,ta}.yaml}
    translate/{indictrans.py, llm_fallback.py, placeholders.py}
    tts/{edge.py, parler.py, postprocess.py}
    schemas.py
  ml/
    intent/{generate_data.py, build_dataset.py, train.py, evaluate.py, export_onnx.py, README.md}
    stt_benchmark/{prepare_clips.py, run_benchmark.py, results/}
  tests/
fixtures/audio/               # shared fixtures you produce
docs/MODEL_REPORT.md
```

## 3. Tech and libraries

Python 3.12, FastAPI, uvicorn, Pydantic v2, `faster-whisper`, `silero-vad`, `onnxruntime`, `transformers`, `optimum` (ONNX export and quantisation), `torch` (CPU wheel in the service image, GPU wheel only on Colab), `soundfile`, `librosa` or `torchaudio`, ffmpeg (system), `jiwer` (WER), `edge-tts`, `IndicTransToolkit` (preprocessing for IndicTrans2), `pyyaml`, `scikit-learn` (metrics), `datasets`, `httpx` (LLM fallbacks), pytest.

Target hardware: the project VPS, 8 CPU threads, about 30 GB RAM, no GPU. Budget: the AI container may use at most 12 GB RAM and 4 threads (`OMP_NUM_THREADS=4`).

## 4. Language support matrix (demo set first)

| Language | code | IndicTrans2 tag | edge-tts voice (verify with `edge-tts --list-voices`) | Demo |
|---|---|---|---|---|
| English | en | eng_Latn | en-IN-NeerjaNeural | yes |
| Hindi | hi | hin_Deva | hi-IN-SwaraNeural | yes |
| Malayalam | ml | mal_Mlym | ml-IN-SobhanaNeural | yes |
| Tamil | ta | tam_Taml | ta-IN-PallaviNeural | yes |
| Telugu | te | tel_Telu | te-IN-ShrutiNeural | stretch |
| Kannada | kn | kan_Knda | kn-IN-SapnaNeural | stretch |
| Bengali | bn | ben_Beng | bn-IN-TanishaaNeural | stretch |
| Marathi | mr | mar_Deva | mr-IN-AarohiNeural | stretch |

Build the service so adding a language is a config change (`models.yaml` plus a lexicon file plus training data), not a code change.

## 5. Phase plan

### Phase 0 — Setup
- Scaffold the service and Dockerfile. Layer the image so model weights live in the `models` volume (mounted at the Hugging Face cache path), not baked into the image.
- `/healthz` returns `{"status":"ok","models":{...}}` with each model reported as `loaded`, `stub` or `unavailable`.
- Auth dependency: require `X-Internal-Token`; 401 otherwise.

### Phase 1 — Stub mode and benchmark prep (be fast: others depend on you)

**1.1 Stub engines.** With env `AI_STUB=true` every endpoint returns canned but contract-valid output:
- `/v1/tts`: returns a 1 second sine wave WAV (8 kHz mono PCM16) with correct headers.
- `/v1/translate`: returns segments prefixed with `[{lang}] ` and placeholders untouched.
- `/v1/stt`, `/v1/speech-intent`: return text `yes`, intent `confirm`, confidence 0.9, unless the uploaded filename contains `no` (then `decline`) or `noise` (then `unclear`, confidence 0.2).
- `/v1/intent`: simple keyword check.
Merge this within the first few hours and tell Members 1 and 2.

**1.2 Audio fixtures.** Record on a phone (voice memo is fine), at least 3 speakers if possible, for each demo language: `yes`, `no`, `later`, `stop`, and `noise` (background talk or silence), saying natural phrases ("haan, main aaunga", "illa, varan pattilla", "ஆம் வருவேன்", "yes, I will come"). Convert to the phone profile with ffmpeg:
```
ffmpeg -i in.m4a -ac 1 -ar 8000 -acodec pcm_s16le out_8k.wav
```
Keep both original and 8 kHz versions. Name them `fixtures/audio/{label}_{lang}_{speaker}.wav` and also the short names required by contract section 13 (`yes_hi.wav` and so on). Get consent from every speaker; do not use any third party's voice.

**1.3 Audio utilities.** `audio/io.py`: load any WAV or MP3 bytes, convert to mono float32. `audio/resample.py`: resample 8 kHz to 16 kHz (the models need 16 kHz) with `soxr` or `librosa`. `audio/vad.py`: silero-vad to trim leading and trailing silence and return speech duration; if speech duration is under 0.3 s return `no_speech`.

**1.4 STT benchmark harness (`ml/stt_benchmark`).**
Build the evaluation set: your fixtures plus a small public set per language (for example FLEURS test clips) downsampled and compressed to simulate phone audio (`-ar 8000` and a low bitrate AMR or MP3 round trip). Use 20 to 40 clips per language. Reference transcripts written by native speakers on the team. Metric: WER and CER with `jiwer`, plus latency per clip on the VPS. Candidates (verify names): `faster-whisper` small and medium (int8), AI4Bharat IndicConformer multilingual, Groq-hosted Whisper large-v3 as a reference upper bound. Output a CSV and a markdown table in `ml/stt_benchmark/results/`.

**1.5 Start data generation for intent** (details in 5.3, run in parallel).

### Phase 2 — Real TTS and prompts for Phase 2 calls
Implement `/v1/tts` for real (before the Exotel keypad test):
- `tts/edge.py`: call `edge_tts.Communicate(text, voice)` and collect MP3 bytes. Retry 3 times with backoff on network errors.
- `tts/postprocess.py`: convert to the call format using ffmpeg: mono, 8 kHz, PCM16 WAV, normalise loudness to about -16 LUFS (`loudnorm`), trim leading silence, add 150 ms silence at the end. Return duration.
- Text clean-up before synthesis: collapse whitespace, expand `Rs.` and `INR` to spoken words per language, put a comma pause between date parts. Keep a small `pronunciation.yaml` for words that TTS mispronounces (event names). Never send phone numbers or personal data to TTS (the API never sends any).
- Return headers `X-Duration-Ms` and `X-Tts-Model`.
- Hindi and English must be real before the first Exotel call; the other languages follow in Phase 4.

### Phase 3 — Real intent: rules, then model

**3.1 Lexicon rules (`intent/rules.py`).** Rules run first and are cheap. Normalise text first: lowercase, strip punctuation, normalise Unicode (NFC), collapse repeated characters, map digits spoken as words. For each language keep a YAML lexicon with `confirm`, `decline`, `reschedule`, `call_later`, `stop_calling` phrase lists, including **romanised and code-mixed forms** ("haan", "nahi", "illa", "aam" and similar). Seed lists (have a native speaker review them, they are starting points):

- English: confirm `yes, yeah, yep, sure, okay, ok, i will come, i'll come, confirmed, count me in`; decline `no, nope, not coming, cannot come, can't come, won't come`; reschedule `reschedule, another time, different time, change the time`; call_later `call later, call me later, busy now, not now`; stop `stop calling, do not call, don't call, remove my number`.
- Hindi (Devanagari and romanised): confirm `हाँ, हां, जी हाँ, ठीक है, आऊंगा, आऊंगी, haan, ji haan, theek hai, aaunga, aaungi`; decline `नहीं, नही, नहीं आ पाऊंगा, nahi, nahin, nahi aa paunga`; call_later `बाद में, अभी नहीं, baad mein, abhi nahi`; reschedule `दूसरा समय, समय बदलो, dusra time`; stop `कॉल मत करो, फोन मत करो, call mat karo, band karo`.
- Malayalam: confirm `അതെ, ശരി, വരാം, വരും, ok, sheri, varam, varum`; decline `ഇല്ല, വരില്ല, പറ്റില്ല, illa, varilla, pattilla`; call_later `പിന്നെ, പിന്നീട്, pinne, pinneed`; stop `വിളിക്കരുത്, vilikkaruth`.
- Tamil: confirm `ஆம், சரி, வருவேன், aam, sari, varuven`; decline `இல்லை, வரமாட்டேன், illai, varamatten`; call_later `பிறகு, அப்புறம், piragu, appuram`; stop `அழைக்காதீர்கள், azhaikkadheenga`.

Matching: token or phrase match with word boundaries, longest phrase wins, negation handling ("nahi" overrides "theek hai" if both appear). Rules return confidence 0.95 on a single clear match, 0.0 when ambiguous (multiple conflicting intents) so the model decides. Empty or very short unmatched text returns `unclear` at 0.3.

**3.2 Dataset (`ml/intent/*`), see 5.3 below.** Train, evaluate, export.

**3.3 Model serving (`intent/model.py`).** Load the ONNX int8 model and tokenizer with `onnxruntime`; `softmax` over logits; return label and confidence. Calibrate: fit temperature scaling on the validation set and store the temperature in `models.yaml`, so confidence is meaningful for the threshold (default 0.6).

**3.4 LLM fallback (`intent/llm_fallback.py`).** Only used when rules gave nothing and the model confidence is below threshold. Gemini (free tier) first, Groq second, otherwise skip. Send **only the transcript text**, never audio or any personal data. Prompt with strict JSON output: `{"intent": "<one of allowed>", "confidence": <0..1>}`. Parse defensively; on any error return `unclear`. Rate limit and cache by transcript hash. Make it switchable by env `LLM_FALLBACK` (contract section 11) and default it to `none` so the privacy claim "no third-party processing" is true unless turned on. If it is on, `source = "llm"` is returned and counted in the report.

**3.5 Pipeline (`intent/pipeline.py`).** Order: rules (if confidence at least 0.9 return) then model (return if confidence at least threshold) then LLM fallback then `unclear`. Respect `allowed_intents` by masking disallowed labels (for example the payment preset has no `reschedule`).

### Phase 4 — Real STT, translation, speech-intent, all demo languages

**4.1 STT router (`stt/router.py`).** From the benchmark choose the best engine per language and store the mapping in `models.yaml` (for example `hi: indic-conformer`, `en: faster-whisper-small`). The `language` hint selects the engine; with no hint, detect with Whisper language ID restricted to the supported set. Always: VAD trim, resample to 16 kHz, cap input at 10 s, run in a thread pool with at most 2 concurrent jobs (semaphore) so the CPU is not overloaded; queue the rest with a 10 s timeout returning HTTP 503 `stt_busy`.
Whisper settings: `beam_size=1`, `temperature=0`, `vad_filter=False` (you already ran VAD), `condition_on_previous_text=False`, `language` set from the hint, `initial_prompt` containing typical reply words for that language to bias recognition (for example "haan, nahi, ji, theek hai, baad mein").
Confidence: average of token probabilities converted to 0..1; document how it is computed.

**4.2 `/v1/speech-intent`.** Pipeline: decode, VAD, STT, intent pipeline. Return the union response in the contract. Measure and log (without transcripts) stage timings: `vad_ms`, `stt_ms`, `intent_ms`. Target under 4 s for a 5 s utterance. If STT dominates, try in this order: smaller model, `cpu_threads=4` and int8, shorter `max_seconds` from Member 2 (6 s), IndicConformer ONNX.

**4.3 Translation (`translate/`).**
- `placeholders.py`: before translation replace each `{key}` with a protected token that survives MT (for example `⟦0⟧`), keep a map, and after translation restore. Validate the set of placeholders is identical; otherwise retry with the LLM fallback; otherwise HTTP 422 `placeholder_lost` with the missing keys in `details`.
- `indictrans.py`: load IndicTrans2 English to Indic distilled (about 200M) and, for completeness, Indic to English. Use `IndicTransToolkit` preprocessing. Batch all segments of a template in one call. Cache results in memory by `(text, src, tgt)`.
- Style: before translation, make the English source TTS-friendly (short sentences). After translation, run a sanity check: output must contain characters of the target script (for Indic targets), length ratio between 0.5 and 3.0 of the source, no leftover English words except protected tokens and allow-listed names.
- Output must keep the sentence-level structure so that TTS pauses are natural.
- Mixed-script policy: leave `{event_name}`, `{venue}` and `{org_name}` values as supplied (Member 1 inserts them after translation). Document for organisers that they can add per-language overrides for these.

**4.4 TTS for all demo languages.** Same as Phase 2. Listen to every generated prompt for the four languages with a native speaker on the team and adjust text clean-up or voice. Optional: evaluate Indic Parler-TTS on Colab for the languages where edge voices sound poor; if used, pre-render there and keep the same API by loading the model in the service only if a GPU or enough CPU time is available (otherwise mark `unavailable` in health).

### Phase 5 — Report and hardening
- Write `docs/MODEL_REPORT.md` (section 7 below).
- Load test: 10 concurrent `/v1/speech-intent` calls, record p50, p95 and memory use.
- Pin all model versions and checksums in `models.yaml`; add a script `scripts/download_models.sh` that fetches them into the volume, so redeploy is repeatable.
- Verify that the service makes **no outbound network calls** when `LLM_FALLBACK=none` and TTS engine is `parler` (use a container with no network to test). edge-tts needs internet; state it.

### Phase 6 — Demo support
- Prepare 6 to 8 spoken phrases per language that are known to work and rehearse them with the person who will demo.
- Ensure models are preloaded at container start (warm-up request in the startup hook) so the first demo call is not slow.

## 5.3 Intent model: data, training, export (details)

**Labels (6):** `confirm, decline, reschedule, call_later, stop_calling, unclear`.

**Data generation (`generate_data.py`).** Use Gemini free tier or Llama via Groq or a local model. For each language in `en, hi, ml, ta` and each label, generate 400 to 600 short utterances (1 to 12 words) in these styles, with a mix proportion you control:
1. Native script, natural phrasing.
2. Romanised (Latin-script) spelling as a person or ASR might write it.
3. Code-mixed (Hinglish, Manglish, Tanglish) with English words such as "come", "sure", "later", "busy", "time".
4. Polite and impolite forms, with fillers ("umm", "haan haan").
5. ASR-noisy variants: drop or swap letters, split words, wrong spaces, homophone-like substitutions.
Prompt design: ask for JSON lines `{"text": ..., "label": ..., "lang": ...}`, give 5 seed examples per label from the lexicon, ask for diversity, forbid duplicates. For `unclear` include: unrelated statements ("who is this"), questions ("what event?"), noise words, partial words, background-speech fragments, single fillers, and empty-like strings ("hmm", "..."). Deduplicate case-insensitively, drop anything that matches the wrong lexicon rule (label noise filter), and sample 100 rows per language for a manual check by a native speaker; fix or remove errors.

**Splits (`build_dataset.py`).** Train 80, validation 10, test 10, stratified by language and label. Create a second **hand-written test set** of at least 50 utterances per language written by team members who did not see the generated data (this is the honest number to report). Store datasets as JSONL in `ml/intent/data/` (not committed if large; commit a 200-row sample).

**Training (`train.py`).** Base model `google/muril-base-cased` (verify name). Hugging Face `Trainer`. Settings: max length 64, batch size 32, learning rate 3e-5, 4 epochs, weight decay 0.01, warmup ratio 0.1, seed fixed, class weights if imbalanced. Run on Colab or Kaggle GPU; on the VPS CPU it is feasible for this data size but slow. Save the best checkpoint by validation macro F1.

**Evaluation (`evaluate.py`).** Per-language and overall: accuracy, macro F1, per-class precision and recall, confusion matrix, on both the synthetic test and the hand-written test. Also evaluate on text produced by the real STT from your audio fixtures (end to end). Targets from the PRD: macro F1 at least 0.90 on synthetic test, at least 0.80 on the hand-written test.

**Export (`export_onnx.py`).** Export with `optimum` to ONNX, apply dynamic int8 quantisation, verify output equivalence (max abs logit diff tolerance and identical argmax on 500 samples), save `model.onnx`, tokenizer files and `labels.json`, copy into the `models` volume. Record model size and CPU latency (target under 150 ms for one sentence on 4 threads).

**If time is short:** skip fine-tuning and ship rules plus LLM fallback, then fine-tune later. Keep the model integration code ready (`intent/model.py`) with a feature flag. Fine-tuning is graded as a plus, but a working pipeline is the priority.

## 6. Error handling and limits

| Condition | Response |
|---|---|
| Missing or wrong `X-Internal-Token` | 401 `unauthorized` |
| Unsupported language | 400 `unsupported_language` |
| Audio longer than 10 s | truncated to 10 s, response includes `"truncated": true` |
| Audio undecodable | 422 `bad_audio` |
| No speech detected | 200 with `no_speech: true`, intent `unclear`, confidence 0.0 |
| STT queue full | 503 `stt_busy` |
| Placeholder lost after retries | 422 `placeholder_lost` |
| TTS engine failure after retries | 502 `tts_failed` |

Request size limits: audio 2 MB, text 2000 characters, segments 20 per translate call.

## 7. `docs/MODEL_REPORT.md` contents

1. Models used (name, version, licence, size, where it runs, purpose).
2. STT benchmark table: WER and CER per model per language, latency, and the chosen engine per language with a one-line reason.
3. Intent: dataset description (sizes, generation method, review), results per language (synthetic and hand-written), confusion matrix summary, confidence calibration, threshold choice, share of decisions made by rules, model, and fallback.
4. Translation: model, approach, placeholder safety, review process, sample outputs for the four languages.
5. TTS: engines, voices, post-processing, listening test notes.
6. End-to-end latency table (VAD, STT, intent, total) p50 and p95.
7. Processing-location facts for Member 1's `PRIVACY.md`: which models run on our server, which calls leave it (edge-tts, optional LLM fallback), what data each receives.
8. Limitations and next steps (more languages, dialects, noisy audio, speaker variety, larger fine-tune set, replace edge-tts with self-hosted TTS).

## 8. Rules and pitfalls

- Phone numbers, names and recordings never enter this service's logs. Do not log transcripts. Log lengths, timings, language and label only.
- The service stores nothing: no audio, no transcripts, no caches on disk containing user data. The translate cache holds template text only.
- Keep the response shapes in contract section 7 byte-for-byte. Add fields only after a `contract-change` PR.
- Do not download models at request time. Models load at startup from the volume.
- Do not run heavy training on the VPS during the demo window.
- Do not use any voice or audio you do not have permission to use.
- Verify licences: some multilingual TTS models are non-commercial. State the licence in the report.

## 9. Hand-offs

| To or from | What | When |
|---|---|---|
| to M1, M2 | stub mode live, contract-valid | first hours of Phase 1 |
| to M2 | audio fixtures, 8 kHz | Phase 1 |
| to M2 | real TTS Hindi and English | before first Exotel call |
| from M2 | real call recordings (with consent) for benchmarking | Phase 2 and 4 |
| to M1 | real translate and tts, all demo languages | start of Phase 4 |
| to M1 | processing-location facts | Phase 5 |
| from M4 | AI container resource limits and volume paths | Phase 0 |

## 10. Definition of done checklist

- [ ] All contract section 7 endpoints implemented, schema-valid, tested.
- [ ] Stub mode available and documented.
- [ ] STT chosen per language from measured WER.
- [ ] Intent pipeline: rules, model, fallback, with thresholds.
- [ ] Fine-tuned model exported and loaded, or a documented decision to defer.
- [ ] Translation keeps placeholders in all test cases.
- [ ] TTS audio for the four demo languages reviewed by native speakers.
- [ ] Latency numbers recorded.
- [ ] `docs/MODEL_REPORT.md` complete.
- [ ] No sensitive data in logs (tested).
