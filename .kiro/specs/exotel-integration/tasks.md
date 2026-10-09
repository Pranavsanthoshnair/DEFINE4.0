# Implementation Plan: Exotel Integration

## Overview

Surgical edits to five existing files and one new test file. No new modules are introduced.
Each task targets exactly one file and is independently executable — an agent can pick up any
single task without depending on another task being completed first (implementation tasks are
parallel-safe; the test task depends on all five implementation tasks).

---

## Tasks

- [ ] 1. Fix `ExotelProvider.__init__` base URL construction
  - In `backend/app/telephony/providers/exotel.py`, change `self._base_url` assignment so it
    uses the subdomain as a full hostname:
    ```python
    self._base_url = f"https://{settings.exotel_subdomain}/v1/Accounts/{self._sid}"
    ```
  - Remove the `.api.exotel.com` suffix that the stub hard-codes — `EXOTEL_SUBDOMAIN` is
    expected to be the full hostname (e.g. `api.exotel.in`).
  - _Requirements: 1.1, 2.1_

- [ ] 2. Fix `ExotelProvider.hangup`, `place_call`, `parse_webhook`, and `render_steps`
  - All edits are inside `backend/app/telephony/providers/exotel.py`.

  - [ ] 2.1 Fix `hangup` — correct Status value and add error swallowing
    - Change `data={"Status": "canceled"}` to `data={"Status": "completed"}`.
    - Wrap the entire method body in `try/except Exception as exc:` and log a warning
      `exotel_hangup_failed` on failure without re-raising.
    - Add `resp.raise_for_status()` inside the happy path.
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ] 2.2 Fix `place_call` — add no-SID warning branch
    - After extracting `sid`, add:
      ```python
      if not sid:
          log.warning("exotel_place_call_no_sid", call_id=str(req.call_id), raw_status=raw_status)
      ```
    - _Requirements: 1.6_

  - [ ] 2.3 Fix `parse_webhook` — add `phone_last4` log and missing-RecordingUrl warning
    - Derive `phone_last4 = str(body.get(_FIELD_TO, ""))[-4:] or ""` at the top of the method.
    - After `event_type` is resolved, add a structured log call:
      `log.info("exotel_webhook", kind=kind, event_type=event_type, sid=sid, phone_last4=phone_last4)`
    - In the `elif kind == "recording"` branch, capture `rec_url = body.get(_FIELD_RECORDING_URL, "")`,
      and add:
      ```python
      if not rec_url:
          log.warning("exotel_recording_url_missing", sid=sid)
      data = {"recording_url": rec_url}
      ```
    - _Requirements: 6.2, 13.2_

  - [ ] 2.4 Fix `render_steps` — return `JSONResponse` instead of `dict`
    - Add `from fastapi.responses import JSONResponse` at the top of the file (or at function
      scope if preferred).
    - Change the return type annotation to `JSONResponse`.
    - Replace `return {"flow": rendered}` with `return JSONResponse(content={"flow": rendered})`.
    - _Requirements: 7.6_

- [ ] 3. Add `validate_exotel_config()` to `factory.py`
  - All edits are inside `backend/app/telephony/providers/factory.py`.
  - Add the following function after the existing `_is_valid_cred` / `_exotel_ready` helpers:
    ```python
    def validate_exotel_config() -> None:
        if settings.call_provider.lower() != "exotel":
            return
        required = {
            "EXOTEL_API_KEY":   settings.exotel_api_key,
            "EXOTEL_API_TOKEN": settings.exotel_api_token,
            "EXOTEL_SID":       settings.exotel_sid,
            "EXOTEL_CALLER_ID": settings.exotel_caller_id,
        }
        missing = [k for k, v in required.items() if not _is_valid_cred(v)]
        if missing:
            raise ValueError(
                f"CALL_PROVIDER=exotel but required credentials are missing or "
                f"placeholder: {', '.join(missing)}"
            )
        if not settings.public_base_url.startswith("https://"):
            log.warning(
                "exotel_public_url_not_https",
                public_base_url=settings.public_base_url,
                hint="Exotel requires a public HTTPS callback URL",
            )
        log.info("exotel_config_ok", sid=settings.exotel_sid, subdomain=settings.exotel_subdomain)
    ```
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 4. Fix webhook URL construction in `scheduler.py`
  - All edits are inside `backend/app/telephony/scheduler.py`, in `execute_place_call`.
  - Replace the existing `flow_url` / `status_callback_url` assignment block with:
    ```python
    base = settings.public_base_url.rstrip("/")
    secret = settings.webhook_secret
    flow_url = f"{base}/webhooks/{secret}/flow?call_id={call_id}"
    status_callback_url = f"{base}/webhooks/{secret}/status"
    ```
  - Remove the trailing `?call_id={call_id}` from the old `status_callback_url` line — the
    `call_id` for status callbacks is recovered from `CustomField` in Exotel's POST body.
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [ ] 5. Wire `validate_exotel_config()` into application startup in `main.py`
  - All edits are inside `backend/app/main.py`.
  - Inside the `lifespan` async context manager, add the Exotel validation call before the
    existing `log.info("veylo_api_started", ...)` line:
    ```python
    if settings.call_provider.lower() == "exotel":
        from app.telephony.providers.factory import validate_exotel_config
        validate_exotel_config()
    ```
  - The `ValueError` raised by `validate_exotel_config` will propagate out of `lifespan` and
    prevent the server from starting — this is the intended fail-fast behaviour.
  - _Requirements: 9.1, 9.4_

- [ ] 6. Add `hypothesis>=6.100.0` to `requirements.txt`
  - In `backend/requirements.txt`, add `hypothesis>=6.100.0` under the `# Testing` section,
    pinned to a minimum of `6.100.0`.
  - _Requirements: (enables property-based tests in task 7)_

- [ ] 7. Create `backend/tests/telephony/test_exotel_provider.py` with 24 unit tests and 6 property tests
  - Create the file `backend/tests/telephony/test_exotel_provider.py`.
  - All HTTP calls to `httpx.AsyncClient` must be intercepted with `respx.mock`; no real network
    calls are made.
  - `render_steps` and `parse_webhook` are pure functions — no mocking is needed for those tests.
  - Each property test must use `@settings(max_examples=100)` and include the tag comment:
    `# Feature: exotel-integration, Property N: <property text>`

  - [ ] 7.1 Write unit tests for `parse_webhook` — flow endpoint (5 tests)
    - `test_parse_webhook_flow_answered` — no AmdResult, no Digits → `event_type = "answered"` (Req 3.5)
    - `test_parse_webhook_flow_amd_result` — AmdResult present → `event_type = "amd_result"` (Req 3.3)
    - `test_parse_webhook_flow_dtmf` — Digits present, no AmdResult → `event_type = "dtmf"` (Req 3.4)
    - `test_parse_webhook_input` — kind=input, Digits present → `event_type = "dtmf"` (Req 5.1)
    - `test_parse_webhook_input_empty_digits` — kind=input, Digits absent → `data = {"digits": ""}` (Req 5.2)
    - _Requirements: 3.3, 3.4, 3.5, 5.1, 5.2_

  - [ ] 7.2 Write unit tests for `parse_webhook` — status endpoint (5 tests)
    - `test_parse_webhook_status_completed` — Status=completed → type, duration, hangup_cause (Req 4.3)
    - `test_parse_webhook_status_no_answer` — Status=no-answer → type=no_answer (Req 4.5)
    - `test_parse_webhook_status_failed` — Status=failed → type=failed (Req 4.6)
    - `test_parse_webhook_status_ringing` — Status=ringing → type=ringing, data={} (Req 4.1)
    - `test_parse_webhook_status_in_progress` — Status=in-progress → type=answered (Req 4.2)
    - _Requirements: 4.1, 4.2, 4.3, 4.5, 4.6_

  - [ ] 7.3 Write unit tests for `parse_webhook` — recording endpoint (2 tests)
    - `test_parse_webhook_recording` — RecordingUrl present → type=recording_ready, url in data (Req 6.1)
    - `test_parse_webhook_recording_missing_url` — RecordingUrl absent → `recording_url=""`, warning logged (Req 6.2)
    - _Requirements: 6.1, 6.2_

  - [ ] 7.4 Write unit tests for `render_steps` (6 tests)
    - `test_render_steps_play` — Play step → `{"action": "play", "url": ...}` (Req 7.1)
    - `test_render_steps_gather_with_prompt` — Gather with prompt_audio_url → includes `"playUrl"` (Req 7.2)
    - `test_render_steps_gather_no_prompt` — Gather without prompt → no `"playUrl"` key (Req 7.2)
    - `test_render_steps_record` — Record step → correct keys and values (Req 7.3)
    - `test_render_steps_hangup` — Hangup step → `{"action": "hangup"}` (Req 7.4)
    - `test_render_steps_empty` — empty list → body is `{"flow": []}` (Req 7.7)
    - All tests assert `isinstance(result, JSONResponse)` (Req 7.6)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.6, 7.7_

  - [ ] 7.5 Write unit tests for `validate_exotel_config` (5 tests)
    - `test_validate_config_raises_missing_key` — blank EXOTEL_API_KEY → ValueError lists key name (Req 9.1)
    - `test_validate_config_raises_missing_caller_id` — blank EXOTEL_CALLER_ID → ValueError (Req 9.4)
    - `test_validate_config_warns_non_https` — http:// PUBLIC_BASE_URL → warning logged, no exception (Req 9.2)
    - `test_validate_config_ok_logs_info` — all creds valid → `exotel_config_ok` info logged (Req 9.5)
    - `test_validate_config_skips_when_mock` — CALL_PROVIDER=mock → no exception even if creds absent (Req 9.3)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ] 7.6 Write unit tests for `place_call` and `hangup` (3 tests, using `respx.mock`)
    - `test_place_call_no_sid_warning` — 2xx but empty CallSid → `accepted=False`, warning logged (Req 1.6)
    - `test_hangup_swallows_http_error` — hangup POST returns 500 → no exception raised (Req 2.3)
    - `test_hangup_uses_completed_status` — verify POST body contains `Status=completed` (Req 2.1)
    - _Requirements: 1.6, 2.1, 2.3_

  - [ ]* 7.7 Write property test for `parse_webhook` idempotency key — always non-empty (Property 1)
    - **Property 1: parse_webhook always produces a non-empty idempotency key**
    - Use `st.one_of(...)` to generate payloads for all four kinds (`flow`, `status`, `input`, `recording`)
      with `st.text()` / `st.uuids()` / `st.integers()` for field values.
    - Assert `event.idempotency_key != ""` for every generated payload.
    - `@settings(max_examples=100)`
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 5.1, 6.1, 12.1, 12.2**

  - [ ]* 7.8 Write property test for `render_steps` — JSONResponse with matching flow length (Property 2)
    - **Property 2: render_steps produces a JSONResponse with a "flow" key of matching length**
    - Build a Hypothesis composite strategy that generates `list[CallStep]` from
      `st.lists(st.one_of(play_strategy, gather_strategy, record_strategy, hangup_strategy))`.
    - Assert `isinstance(result, JSONResponse)` and `len(json.loads(result.body)["flow"]) == len(steps)`.
    - `@settings(max_examples=100)`
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7**

  - [ ]* 7.9 Write property test for `parse_webhook` determinism (Property 3)
    - **Property 3: parse_webhook is deterministic — identical payloads produce identical idempotency keys**
    - For each generated payload, call `parse_webhook` twice with the same arguments.
    - Assert `event1.idempotency_key == event2.idempotency_key`.
    - `@settings(max_examples=100)`
    - **Validates: Requirements 12.3**

  - [ ]* 7.10 Write property test for `parse_webhook` Status sensitivity (Property 4)
    - **Property 4: parse_webhook is sensitive to Status — payloads differing only in Status produce different idempotency keys**
    - Generate a base status payload and a second payload identical except `Status` differs (e.g. `"ringing"` vs `"completed"`).
    - Assert `event1.idempotency_key != event2.idempotency_key`.
    - `@settings(max_examples=100)`
    - **Validates: Requirements 12.4**

  - [ ]* 7.11 Write property test for `validate_exotel_config` missing credentials (Property 5)
    - **Property 5: validate_exotel_config raises ValueError for any combination of missing required credentials**
    - Use `st.sets(st.sampled_from(["EXOTEL_API_KEY", "EXOTEL_API_TOKEN", "EXOTEL_SID", "EXOTEL_CALLER_ID"]),
      min_size=1)` to choose which creds to blank out.
    - Monkeypatch `settings` for each draw, call `validate_exotel_config()`, assert `ValueError` is raised
      and every blanked-out key name appears in the error message.
    - `@settings(max_examples=100)`
    - **Validates: Requirements 9.1, 9.4**

  - [ ]* 7.12 Write property test for webhook URL construction (Property 6)
    - **Property 6: Webhook URL construction strips trailing slashes and correctly places call_id**
    - Use `st.uuids()` for `call_id` and `st.text(alphabet=st.characters(whitelist_categories=("L","N")), min_size=1)`
      for base URL suffix; generate base URLs with and without trailing slash.
    - Invoke the URL-building logic directly (extract as a helper or test via a call to `execute_place_call`
      with DB mocked out).
    - Assert `flow_url.endswith(f"/flow?call_id={call_id}")` and `status_callback_url.endswith("/status")`.
    - Assert `"call_id" not in status_callback_url`.
    - `@settings(max_examples=100)`
    - **Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5**

- [ ] 8. Final checkpoint — ensure all tests pass
  - Run `pytest backend/tests/telephony/test_exotel_provider.py -v` and verify all 24 unit tests
    and all 6 property tests pass.
  - Ensure no import errors in the five modified files.
  - Ask the user if any questions arise.

---

## Notes

- Tasks 1–6 each touch exactly one file and are fully independent — they can be executed in any order or in parallel.
- Task 7 (tests) depends on tasks 1–6 being complete because the tests import and exercise the fixed code.
- Sub-tasks marked with `*` are optional and can be skipped for a faster MVP; the 24 unit tests in 7.1–7.6 provide baseline coverage without them.
- Each task references specific requirements for traceability.
- Property tests validate universal correctness guarantees; unit tests validate specific examples and edge cases.
- All HTTP calls must be intercepted with `respx.mock` — no real network calls.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1", "2.1", "2.2", "2.3", "2.4", "3", "4", "5", "6"] },
    { "id": 1, "tasks": ["7.1", "7.2", "7.3", "7.4", "7.5", "7.6"] },
    { "id": 2, "tasks": ["7.7", "7.8", "7.9", "7.10", "7.11", "7.12"] }
  ]
}
```
