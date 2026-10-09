# Member 2 — Telephony and Call Orchestration

**You own:** the call provider layer (mock and Exotel), the flow engine (the call state machine), webhook handlers, the dispatcher and scheduler, retries, voicemail handling, calling windows, concurrency control, recording fetch, and the calling-approach document.

**Read first:** `PRD.md` and `CONTRACTS.md` (sections 3, 8, 9, 10 are yours; 4 and 7 you consume).

**If you are using an AI coding agent:** give it this file plus `CONTRACTS.md`. The agent must follow the `CallProvider` interface, outcome vocabulary, retry table and flow table exactly. Anything about Exotel marked VERIFY must be implemented behind configuration, never hard-coded from memory.

---

## 1. What you deliver

1. `CallProvider` interface, `MockProvider`, `ExotelProvider`.
2. Flow engine as a pure, unit-tested function.
3. Webhook handlers (`flow`, `status`, `input`, `recording`) with idempotency.
4. Dispatcher (`dispatch_due_calls`), `place_call`, `fetch_recording`, `sweep_stuck_calls` Celery tasks.
5. Retry logic, calling window logic, concurrency and rate limiting.
6. Voicemail branch.
7. Mock scenarios (contract section 9.6) that drive the real webhooks.
8. Answers to the Exotel VERIFY list, written into `CONTRACTS.md` section 8.3.
9. `docs/CALLING_APPROACH.md`.
10. Tests: unit tests for the flow engine for every row in the contract tables, integration tests with the mock.

## 2. Directory ownership

```
services/api/app/telephony/
  router.py                   # exposes /webhooks/... and is included by main.py
  webhooks.py
  providers/{base.py, mock.py, exotel.py, factory.py}
  flow/{engine.py, context.py, steps.py}
  scheduler.py                # dispatch logic
  tasks.py                    # Celery tasks
  retry.py                    # retry policy and window math
  recordings.py
services/api/tests/telephony/
docs/CALLING_APPROACH.md
```
You read and write the tables `calls`, `call_events`, `intents`, and update `campaign_contacts` and `contacts.opted_out`. You never change their definitions: ask Member 1 via a `contract-change` PR.

## 3. Tech and libraries

Python 3.12, FastAPI routers, httpx (async), Celery, Redis (`redis-py`), SQLAlchemy 2.0, `zoneinfo`, `tenacity` (retries on provider HTTP calls), pytest with `respx` for mocking httpx.

## 4. Core design (read before coding)

- **The flow engine is a pure function.** `next(call_ctx, event) -> FlowDecision`. It does no I/O. The webhook handler loads context, calls the engine, then performs the effects (DB writes, AI calls, HTTP response). This keeps 90 percent of your logic testable without a phone.
- **Neutral steps.** The engine returns `Play`, `Gather`, `Record`, `Hangup`. Only `provider.render_steps()` knows the provider format.
- **Speech classification is an effect, not engine logic.** When a recording arrives, the handler downloads the audio, calls `ai.speech_intent`, then feeds a normalised `speech_result` event back into the engine. Add that event type to the engine: `SpeechResult(text, intent, confidence)`.
- **Everything is idempotent.** `call_events.idempotency_key` is unique. Build the key as `sha256(provider + provider_call_sid + event_type + stable_payload_fields)`. If the insert conflicts, return HTTP 200 immediately.
- **Locking.** When handling an event for a call, lock the call row with `SELECT ... FOR UPDATE` so two simultaneous webhooks cannot both advance the flow.
- **Never decrypt a phone number outside `place_call`.** Use `reveal_phone(contact)` from Member 1.

## 5. Phase plan

### Phase 0 — Setup
Create `app/telephony/` package skeleton and an empty router that returns 200 on `/webhooks/{secret}/status`. Agree the `ProviderEvent` and step dataclasses with Member 1 (they are in contracts section 8.1; copy them exactly).

### Phase 1 — Provider layer, flow engine, scheduler on the mock

**1.1 Base types.** Implement the dataclasses and `Protocol` exactly as in the contract. Put `factory.get_provider()` reading `CALL_PROVIDER`.

**1.2 Flow engine (`flow/engine.py`).**
Implement the table in contract 9.2 and the voicemail branch in 9.3 as code. Context object:

```python
@dataclass
class CallContext:
    call_id: UUID
    language: str
    amd_result: str | None
    flow_state: dict            # reprompts, no_input_count, speech_attempts, branch
    template: TemplateView      # dtmf_map, speech_enabled, voicemail_policy
    audio: dict[str, str]       # segment_key -> public wav URL for this language
    speech_threshold: float
```
Events: `Answered`, `AmdResult(value)`, `Digits(value)`, `Timeout`, `RecordingReady(url)`, `SpeechResult(...)`, `Completed(status, duration, hangup_cause)`.
Decision: `FlowDecision(steps, intent, outcome, finalize, new_flow_state, opt_out)`.
Rules recap you must encode:
- Prompt step always combines `Play(greeting)` then `Gather(prompt)`. If `speech_enabled`, add `Record` after the Gather so a caller can talk instead of pressing.
- Digit in `dtmf_map` gives an intent with confidence 1.0, then `Play(ack_*)` then `Hangup`.
- One re-prompt maximum for unclear input, one re-prompt maximum for silence (separate counters).
- Intent `stop_calling` always wins and sets `opt_out=True`.
- Voicemail branch per template policy.
Write a unit test for **every row** of the table in contract 9.2 plus these edge cases: digit pressed during the greeting, two digits pressed quickly (use the first), Completed arrives before any event, duplicate Answered.
Done when: tests are green and cover at least 95 percent of `engine.py`.

**1.3 MockProvider.**
`place_call` returns a fake sid and schedules a simulator coroutine on the worker (use an in-process background task, or a Celery task `telephony.mock_simulate(call_id)`). The simulator decides behaviour from the last two digits of the phone number (contract 9.6) and performs real HTTP requests to the API's own `/webhooks/{secret}/...` endpoints with realistic payloads and short delays (0.2 to 1 s), so the whole stack is exercised. For speech scenarios it posts the recording URL of a fixture file served by the API (`/media/fixtures/...` only in `APP_ENV=dev`). Make timings configurable by env `MOCK_SPEED` (1.0 normal, 0.1 fast tests).

**1.4 Webhook handlers (`webhooks.py`).**
Implement the four HTTP routes and the optional websocket stub (returns 501 for now). Common pipeline:
1. Constant-time compare of `{secret}` with `WEBHOOK_SECRET`; mismatch gives 404 (not 403) so the route is not discoverable.
2. `provider.parse_webhook(...)` gives a `ProviderEvent`.
3. Insert `call_events` (mask numbers in payload before storing). Conflict means return 200 and stop.
4. Load call and context, lock the row, run the engine, persist `flow_state`, `flow_step`, `status`, timestamps.
5. Persist `intents` row when the decision has an intent.
6. If `finalize`: set `calls.outcome`, `ended_at`, update `campaign_contacts` per section 5.4 below, release the concurrency slot, call `maybe_complete(campaign_id)`.
7. Respond with `provider.render_steps(decision.steps)` for flow requests, `200 OK` otherwise.

**1.5 Dispatcher and `place_call` (`scheduler.py`, `tasks.py`).**
Follow contract 9.5 exactly. Details:
- Use one SQL statement with `FOR UPDATE SKIP LOCKED` and `LIMIT free_slots`.
- Concurrency counter in Redis: `INCR` before placing, `DECR` on finalisation or sweep. Never let it go negative (clamp with a Lua script or check).
- `place_call(campaign_contact_id)`: create the `calls` row (`attempt_no = attempts + 1`, status `initiated`), increment `attempts`, load and `reveal_phone`, build `PlaceCallRequest` with `flow_url = {PUBLIC_BASE_URL}/webhooks/{WEBHOOK_SECRET}/flow?call_id={call_id}` and `status_callback_url` similarly, call `provider.place_call`. On provider error (HTTP 5xx, timeout): treat the attempt as `failed` with outcome `failed` and apply retry rules; do not retry inside the task more than 2 times with `tenacity` exponential backoff for network errors only.
- Respect `pr002:rate:exotel` token bucket (default 2 calls per second).

**1.6 Retry and window math (`retry.py`).**
```python
def in_window(now_utc, tz, start, end) -> bool
def next_window_start(now_utc, tz, start, end) -> datetime
def schedule_next_attempt(outcome, attempts, max_attempts, policy, now_utc, tz, start, end) -> tuple[state, next_attempt_at, final_outcome]
```
Rules from contract 9.4. Unit tests with fixed clocks: 20:30 plus 60 minutes lands next day 09:00; DST is irrelevant for IST but test a timezone with DST anyway to prove the logic is correct.

**1.7 Sweeper.** Implement `sweep_stuck_calls` per contract.

**Phase 1 exit (with Member 1):** run all scenarios from the mock table on a 20 contact CSV. All end in the expected outcome and `GET /summary` matches.

### Phase 2 — Exotel integration (starts at kickoff)

**2.1 Answer the VERIFY list first (target: within the first hour with sandbox access).**
Read the official Exotel developer documentation for outbound call API, applets (Passthru, Gather, Play, Record, Voicebot) and status callbacks, then test with a single call using curl. Write answers into contracts section 8.3 and share them in chat. Decide:
- `integration_mode`: `dynamic` if the call API can fetch instructions from a URL we host, otherwise `static`.
- `speech_mode`: `sync` if the caller's audio is available during the call, otherwise `async`.
- `amd_source`: `exotel` if provided, otherwise `heuristic`.
- `audio_format`: what Exotel plays reliably.

**2.2 ExotelProvider (`providers/exotel.py`).**
- HTTP Basic auth with `EXOTEL_API_KEY` and `EXOTEL_API_TOKEN`; base URL built from `EXOTEL_SUBDOMAIN` and `EXOTEL_SID`. Do not guess the field names: copy them from the docs you read and put every field name in a constants block at the top of the file so a mismatch is a one-line fix.
- `place_call`: pass caller id (ExoPhone), destination, the flow or application URL, status callback URL, and our `call_id` in the custom-field parameter so webhooks can be mapped back. Apply a time limit.
- `parse_webhook`: normalise Exotel form or JSON payloads into `ProviderEvent`. Map Exotel statuses (completed, busy, no-answer, failed, canceled) to our `call.status` and outcome. Build the idempotency key from the call sid, status, and any timestamp field Exotel sends.
- `render_steps`: **dynamic mode** returns the response format Exotel expects from a dynamic URL (confirm in docs). **Static mode**: you will configure one flow per language in the Exotel dashboard (greeting, Gather with prompt URL, Passthru to our webhook); `render_steps` then only has to return the small HTTP responses those applets expect, and the call uses audio URLs passed as flow parameters if supported, otherwise pre-uploaded audio (fallback, document it).
- `fetch_recording`: download with auth, stream to a temp file, then encrypt and move (see 2.4).
Write contract tests using recorded real payloads (save sanitised copies in `fixtures/exotel/`).

**2.3 Public URL check with Member 4.** Confirm `https://api.<domain>/webhooks/<secret>/status` is reachable from the internet (use Exotel's own test or a webhook tester), and that `/media/audio/<sha>.wav` plays on a real phone call.

**2.4 Recording handling (`recordings.py`).**
On `recording_ready`: enqueue `telephony.fetch_recording(call_id)`. The task downloads the file, encrypts with `encrypt_bytes`, saves to `RECORDINGS_DIR/{yyyy}/{mm}/{call_id}.bin`, writes `calls.recording_path`, and clears `recording_provider_url`. If download fails, retry 3 times over 10 minutes, then log and keep the provider URL (so retention can still be enforced by Exotel side policy; note this in `CALLING_APPROACH.md`).

**Phase 2 exit:** a real call to a team phone plays greeting and prompt, a keypad digit is recorded in `intents`, the call row shows the correct status and duration, and the recording is stored encrypted.

### Phase 3 — Reliability

Work through the PRD test matrix rows 1 to 10 and 13 to 16 for both mock and real calls (where the sandbox allows). Specific tasks:
- **Voicemail.** Use Exotel AMD if available. Otherwise use the heuristic: treat as `machine` if the first speech segment is longer than 4 s without a pause, or if a beep is detected (requires speech mode and the audio; if neither is possible mark `unknown` and treat as human, then rely on `no_input`). Document the choice and measured false positive rate from your tests.
- **Hang-ups.** Completed before intent means `no_input` with `hangup_cause=caller_hangup`.
- **Failure mapping.** Unknown or invalid number, network failure, provider 4xx and 5xx: outcome `failed`, retry in 15 min, count the attempt.
- **Calling window.** Dispatcher honours it; retry scheduling clamps to the next window.
- **Concurrency.** Test that with `max_concurrent_calls=3` and 50 due contacts there are never more than 3 active calls.
- **Idempotency.** Test by posting every webhook twice.
- **Crash recovery.** Kill the worker mid-call, verify the sweeper recovers.
- **Opt-out.** After `stop_calling`, create a second campaign with the same contact and prove the dispatcher skips it.

### Phase 4 — Speech

- Implement the `Record` step and `recording_ready` handling in the flow: after the caller finishes speaking, download the audio (fast path, stream to memory, not to disk), call `ai.speech_intent`, feed `SpeechResult` into the engine.
- If `speech_mode = async` (audio only available after the call): the in-call fallback to keypad is not possible. Play only the `goodbye` segment and hang up. Do not finalise the call yet: leave `calls.outcome` unset and keep the contact in `in_call`. Classify after the call inside `fetch_recording`, then finalise with the resulting outcome (or `unclear` when confidence is low or the transcript is empty). If classification never completes, the sweeper (15 minutes) fails the call as usual. Do not add a new outcome value. Record this mode clearly in the dashboard (`intents.source = speech`, `latency_ms`).
- Measure end-to-end latency (end of speech to next prompt start) over at least 20 calls. Log p50 and p95 in `CALLING_APPROACH.md`. If p95 is above 4 s, tell Member 3 which stage dominates.
- Test with all four demo languages using fixture audio and real phone calls.

### Phase 5 — Document
Write **`docs/CALLING_APPROACH.md`**:
1. The options table and the hybrid decision (start from `PRD.md` section 6; keep it consistent, add your measured evidence: latency numbers, DTMF versus speech accuracy, voicemail accuracy).
2. Call flow diagram (ASCII or Mermaid) including the voicemail branch and the fallback chain.
3. Which flows are scripted only (payment) and which use speech (seminar, clinic), and why.
4. Real-world behaviours handled (table of outcomes and what triggers each).
5. Compliance behaviours implemented: consent, DND, calling window, opt-out, retries limited.
6. Known limits: sandbox limits, speech accuracy on narrow-band audio, AMD uncertainty, no streaming agent.
7. Future work: streaming voicebot via the Voicebot applet using the same flow engine.

### Phase 6 — Demo support
- A script `scripts/run_scenarios.py` that launches a mock campaign covering all scenarios and prints a pass/fail table (used in the demo as a reliability proof).
- Make `MOCK_SPEED` and a "demo mode" env available so the team can show a fast end-to-end run if the sandbox fails during the demo.

## 6. State update rules (campaign_contacts)

On finalisation of a call with outcome `o`:
- If `o` in `TERMINAL_OUTCOMES`: `state = done`, `final_outcome = o`, `last_outcome = o`.
- Else: set `last_outcome = o` and compute with `schedule_next_attempt`: if attempts remain then `state = waiting_retry` and `next_attempt_at` set; else `state = exhausted` and `final_outcome = o`.
- If the intent was `stop_calling`: also set `contacts.opted_out = true`, `opted_out_at = now()`.
- Always set `last_call_at = now()`.
All inside the same transaction as the call update.

## 7. Rules and pitfalls

- Never trust webhook input: validate types, ignore unknown fields, cap payload size at 64 KB.
- Return quickly. Anything slow (downloading, STT) happens inside the flow request only when `speech_mode = sync`; otherwise queue it.
- Do not log phone numbers, recording URLs, transcripts.
- Do not hold database locks across HTTP calls to the AI service. Read context, release, call AI, then re-lock to apply the result.
- Do not hard-code Exotel field names outside the constants block.
- Never place a call without checking: campaign `running`, inside window, contact `consent`, not `opted_out`, not `dnd`.
- A call's audio URLs must be absolute HTTPS URLs from `PUBLIC_BASE_URL`.
- Do not change outcome names or retry minutes. Tune only through `campaigns.retry_policy`.

## 8. Hand-offs

| From or to | What | When |
|---|---|---|
| from M1 | models, migrations, `reveal_phone`, `maybe_complete`, `encrypt_bytes` | early Phase 1 |
| to M1 | confirmation of call and event write patterns; need for any schema change | Phase 1 |
| from M4 | public HTTPS hostnames and the webhook route reachable from the internet | Phase 2 |
| from M3 | audio fixtures, `speech-intent` endpoint real and stable, latency measurements | Phase 4 |
| to M4 | list of call event types and intents for the call detail drawer; screenshots of real call timeline | Phase 3 |
| to M3 | real recorded phone audio samples (with consent) for benchmarks | Phase 2 and 4 |

## 9. Definition of done checklist

- [ ] Flow engine tests cover every row of the contract tables.
- [ ] Mock scenarios 01 to 10 all end in the expected outcome through the real webhooks.
- [ ] Real Exotel call: greeting, prompt, digit, outcome, recording stored encrypted.
- [ ] Idempotency, concurrency cap, window, sweeper, opt-out tests pass.
- [ ] VERIFY list answered in contracts section 8.3.
- [ ] Latency numbers measured and written down.
- [ ] `docs/CALLING_APPROACH.md` complete.
- [ ] Scenario runner script works.
