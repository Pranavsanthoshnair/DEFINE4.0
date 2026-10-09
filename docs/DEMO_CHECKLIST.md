# AI demo checklist

This checklist covers the current MuRIL intent demo. Keep the label order fixed:
`confirm`, `decline`, `reschedule`, `call_later`, `stop_calling`, `unclear`.

## Required configuration

Set these in `ai/.env` or in the service environment. Never commit the file or
print its values.

- `SARVAM_API_KEY` — required for live Saaras STT, Mayura translation, and Bulbul TTS.
- `AI_INTERNAL_TOKEN` — required by the AI service routes and the test scripts.
- `MODELS_DIR=/models` in Docker, or the local model directory when running directly.
- `LLM_FALLBACK=none` — the demo default.
- `STT_PROVIDER=sarvam` — recommended for the four-language demo.

The current environment check confirms that `SARVAM_API_KEY` is configured in
`ai/.env`; the value was not displayed.

## Model files

For a direct run, the model must be under:

```text
ai/models/intent/
  model.onnx
  labels.json
  tokenizer.json
  tokenizer_config.json
  training_report.json
```

The tokenizer is loaded from this local folder with network access disabled.
The ONNX model uses CPU inference with four threads. MuRIL remains local for
intent; Sarvam remains the provider for STT, translation, and TTS.

## Start the AI service

From the repository root:

```powershell
cd ai
python -m uvicorn app.main:app --host 127.0.0.1 --port 8200
```

For Docker, first resolve and validate the current uncommitted
`docker-compose.yml` merge-conflict state. The intended AI configuration is
`MODELS_DIR=/models` with the host model directory mounted read-only at
`/models`.

## Readiness check

Use the internal self-check without exposing credentials:

```powershell
curl.exe http://127.0.0.1:8200/v1/self-check `
  -H "X-Internal-Token: $env:AI_INTERNAL_TOKEN"
```

Confirm `onnx_model_loaded`, `tokenizer_local`, temperature `0.527`, threshold
`0.7`, the four `stt_mode` values, `ffmpeg_present`, and the boolean
`sarvam_api_key_configured`.

## Voice test commands

Run these from the repository root:

```powershell
python scripts/translation_sanity.py
python scripts/tts_check.py
python scripts/e2e_smoke.py --audio fixtures/audio/yes_en.wav --language en
```

Before live credentials or a running service are available, validate command
paths without making network calls:

```powershell
python scripts/translation_sanity.py --dry-run
python scripts/tts_check.py --dry-run
python scripts/e2e_smoke.py --dry-run
```

TTS outputs are written to `ai/tests/tts_out/`, which is gitignored. The
native-speaker review sheet is
`docs/analysis/native_listening_sheet.csv`.

## Rehearsal

1. Start the AI service and confirm the self-check.
2. Run translation sanity checks and inspect every reported failure.
3. Generate the seminar prompt, reprompt, and four ordinary acknowledgements.
4. Listen to the generated files with native speakers and record corrections in
   the listening sheet. Do not treat synthetic audio as human-quality evidence.
5. Run the smoke test with one reply fixture per language.
6. Test DTMF/tap-to-answer for each allowed label, including a disallowed tap.
7. Test explicit opt-out phrases and verify the stop-calling outcome.
8. Keep a keypad fallback available for unclear speech.

## Known limits

- The documented model-only result is **0.775 accuracy** and **0.784699 macro
  F1** on a synthetic, partly leaky repository test set; it is not a clean
  held-out evaluation.
- Malayalam is weakest at **0.65 accuracy** on that set.
- Training data is Romanized/code-mixed only; native-script performance is not
  established.
- Existing audio fixtures are synthetic TTS/silence fixtures, not human
  recordings.
- The checked-in report's 0.979 result is an in-distribution synthetic result.
- LLM fallback is disabled by default; below-threshold predictions become
  `unclear`.
- Native-speaker listening and live Sarvam checks remain required before an
  Exotel call.

## Approval still required

The tap-to-answer change is implemented and tested, but the corresponding
`docs/CONTRACTS.md` edit remains a contract-change proposal. It should be
approved before changing the shared contract.
