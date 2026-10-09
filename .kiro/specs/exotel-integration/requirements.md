# Requirements Document

## Introduction

This feature makes the `ExotelProvider` class in `backend/app/telephony/providers/exotel.py`
production-ready so that plugging in real Exotel credentials (via environment variables) is
sufficient to place live outbound calls, receive webhooks, and process call recordings — with
no additional code changes required.

The platform already has a working provider abstraction (`CallProvider` in `base.py`), a
`MockProvider` for development and testing, a webhook router (`webhooks.py`), a flow engine,
and a provider factory that auto-selects the correct provider from env vars. The goal of this
spec is to define exactly what the `ExotelProvider` implementation, configuration system, and
webhook parsing layer must do to make all of those pieces work correctly end-to-end with
Exotel's live API.

The `MockProvider` must continue to work without modification when Exotel credentials are absent.

---

## Glossary

- **ExotelProvider**: The class in `providers/exotel.py` that implements `CallProvider` for the
  Exotel telephony platform.
- **MockProvider**: The existing provider that simulates calls without network access; used in
  development and testing.
- **CallProvider**: The abstract interface defined in `providers/base.py` that both providers
  implement.
- **PlaceCallRequest**: Dataclass carrying the call parameters (to-number, caller-id, flow URL,
  status callback URL, custom field, time limit).
- **PlaceCallResult**: Dataclass returned from `place_call` (provider call SID, accepted flag,
  raw status string).
- **ProviderEvent**: Normalised event dataclass returned by `parse_webhook` (type, SID, call_id,
  data dict, idempotency key).
- **CallStep**: Union type (`Play | Gather | Record | Hangup`) representing a neutral step in the
  call flow.
- **Flow URL**: The publicly reachable HTTPS endpoint (`{PUBLIC_BASE_URL}/webhooks/{WEBHOOK_SECRET}/flow`)
  that Exotel calls when a callee answers; it must return rendered call steps.
- **Status Callback URL**: The publicly reachable HTTPS endpoint
  (`{PUBLIC_BASE_URL}/webhooks/{WEBHOOK_SECRET}/status`) that Exotel calls on call status changes.
- **CustomField**: The Exotel API parameter that echoes an arbitrary string back in every webhook;
  used to carry `str(call_id)`.
- **Render**: Converting a `list[CallStep]` into the response body format Exotel's dynamic-mode
  Flow URL expects.
- **AMD**: Answering Machine Detection — Exotel's optional feature that classifies the callee as
  `human`, `machine`, or `unknown` before the call flow continues.
- **EXOTEL_SID**: Exotel account SID environment variable.
- **EXOTEL_API_KEY**: Exotel API key environment variable.
- **EXOTEL_API_TOKEN**: Exotel API token (password) environment variable.
- **EXOTEL_SUBDOMAIN**: Exotel regional API subdomain (e.g. `api.exotel.in`).
- **EXOTEL_CALLER_ID**: The ExoPhone number used as the caller ID for outbound calls.
- **WEBHOOK_SECRET**: Random string embedded in webhook URL paths for security.
- **PUBLIC_BASE_URL**: The publicly reachable HTTPS base URL of the backend service.
- **Config_Validator**: The startup component that checks all required environment variables
  are present when `CALL_PROVIDER=exotel`.

---

## Requirements

### Requirement 1: Outbound Call Placement

**User Story:** As a campaign operator, I want the system to place outbound calls through
Exotel using a dynamic flow URL, so that the call flow is controlled by the backend in
real time without rebuilding a static Exotel dashboard flow for each campaign.

#### Acceptance Criteria

1. WHEN `place_call` is invoked, THE ExotelProvider SHALL send an HTTP POST to
   `https://{EXOTEL_SUBDOMAIN}/v1/Accounts/{EXOTEL_SID}/Calls/connect.json`
   using HTTP Basic Auth with `EXOTEL_API_KEY` as the username and `EXOTEL_API_TOKEN`
   as the password.
2. WHEN `place_call` is invoked, THE ExotelProvider SHALL include the fields `From`
   (set to `EXOTEL_CALLER_ID`), `To` (set to the E.164 destination number),
   `Url` (set to the `flow_url` from `PlaceCallRequest`), `StatusCallback`
   (set to `status_callback_url` from `PlaceCallRequest`), `CustomField`
   (set to `str(call_id)`), and `TimeLimit` (set to `time_limit_sec`) in the POST body.
3. WHEN Exotel returns a 2xx response, THE ExotelProvider SHALL extract the `CallSid`
   field from the `Call` object in the JSON response body and return it as
   `PlaceCallResult.provider_call_sid`.
4. WHEN Exotel returns a 2xx response, THE ExotelProvider SHALL set
   `PlaceCallResult.accepted = True` when the `CallSid` is non-empty.
5. IF Exotel returns a 4xx or 5xx HTTP response, THEN THE ExotelProvider SHALL raise
   an `httpx.HTTPStatusError` without swallowing it, so the Celery task can retry.
6. IF Exotel returns a 2xx response but the `CallSid` field is absent or empty, THEN
   THE ExotelProvider SHALL set `PlaceCallResult.accepted = False` and log a warning
   at `WARNING` level via structlog with the key `exotel_place_call_no_sid`.
7. THE ExotelProvider SHALL set the HTTP request timeout to 10 seconds for
   `place_call` to prevent the Celery task from blocking indefinitely.

---

### Requirement 2: Outbound Call Cancellation

**User Story:** As the scheduler, I want to cancel an in-progress Exotel call, so that
stuck calls can be cleaned up without waiting for the provider timeout.

#### Acceptance Criteria

1. WHEN `hangup` is called with a `provider_call_sid`, THE ExotelProvider SHALL send
   an HTTP POST to
   `https://{EXOTEL_SUBDOMAIN}/v1/Accounts/{EXOTEL_SID}/Calls/{provider_call_sid}.json`
   with the field `Status` set to `"completed"` in the POST body.
2. THE ExotelProvider SHALL use HTTP Basic Auth (API key / token) for the `hangup`
   request.
3. IF the hangup request fails with any HTTP or network error, THEN THE ExotelProvider
   SHALL log the error at `WARNING` level and return without raising, so a hangup
   failure never crashes the sweep task.

---

### Requirement 3: Webhook Parsing — Flow Endpoint

**User Story:** As the webhook handler, I want the flow endpoint to correctly parse
Exotel's POST payload and return a normalised `ProviderEvent`, so that the flow engine
receives the right event type (answered, amd_result, or dtmf) on every call.

#### Acceptance Criteria

1. WHEN the `/webhooks/{secret}/flow` endpoint receives a POST, THE ExotelProvider
   SHALL read the `CallSid` field from the form-encoded body and set it as
   `ProviderEvent.provider_call_sid`.
2. WHEN the flow payload contains a `CustomField` value, THE ExotelProvider SHALL
   parse it as a UUID and set `ProviderEvent.call_id`; if parsing fails, THE
   ExotelProvider SHALL set `call_id = None`.
3. WHEN the flow payload contains an `AmdResult` field with a non-empty value, THE
   ExotelProvider SHALL set `ProviderEvent.type = "amd_result"` and
   `ProviderEvent.data = {"amd": <lowercased AmdResult>}`.
4. WHEN the flow payload contains a `Digits` field with a non-empty value and no
   `AmdResult` field, THE ExotelProvider SHALL set `ProviderEvent.type = "dtmf"` and
   `ProviderEvent.data = {"digits": <Digits value>}`.
5. WHEN the flow payload contains neither `AmdResult` nor `Digits`, THE ExotelProvider
   SHALL set `ProviderEvent.type = "answered"` and `ProviderEvent.data = {}`.
6. THE ExotelProvider SHALL construct the idempotency key from the tuple
   `("exotel", CallSid, event_type, json.dumps({"status": Status, "ts": StartTime},
   sort_keys=True))` using the `make_idempotency_key` helper from `base.py`.

---

### Requirement 4: Webhook Parsing — Status Endpoint

**User Story:** As the webhook handler, I want the status endpoint to correctly parse
Exotel's call-status callbacks, so that the call record is updated with the correct
terminal status and the retry scheduler is triggered with accurate information.

#### Acceptance Criteria

1. WHEN the status payload `Status` field is `"ringing"`, THE ExotelProvider SHALL
   return `ProviderEvent.type = "ringing"` and `data = {}`.
2. WHEN the status payload `Status` field is `"in-progress"`, THE ExotelProvider SHALL
   return `ProviderEvent.type = "answered"` and `data = {}`.
3. WHEN the status payload `Status` field is `"completed"`, THE ExotelProvider SHALL
   return `ProviderEvent.type = "completed"` and
   `data = {"status": "completed", "duration": int(Duration), "hangup_cause": HangupCause}`.
4. WHEN the status payload `Status` field is `"busy"`, THE ExotelProvider SHALL return
   `ProviderEvent.type = "busy"` and
   `data = {"status": "busy", "duration": 0, "hangup_cause": ""}`.
5. WHEN the status payload `Status` field is `"no-answer"`, THE ExotelProvider SHALL
   return `ProviderEvent.type = "no_answer"` and
   `data = {"status": "no_answer", "duration": 0, "hangup_cause": ""}`.
6. WHEN the status payload `Status` field is `"failed"` or `"canceled"` or is absent
   or unrecognised, THE ExotelProvider SHALL return `ProviderEvent.type = "failed"`
   and `data = {"status": "failed", "duration": 0, "hangup_cause": "unknown"}`.
7. THE ExotelProvider SHALL normalise all `Status` values to lowercase and replace
   spaces with hyphens before lookup, so that minor casing variations in Exotel's
   payload do not cause misclassification.

---

### Requirement 5: Webhook Parsing — Input Endpoint

**User Story:** As the webhook handler, I want the input endpoint to correctly parse
DTMF digit callbacks sent separately from the flow request, so that keypad responses
are reliably captured even when Exotel delivers them asynchronously.

#### Acceptance Criteria

1. WHEN the `/webhooks/{secret}/input` endpoint receives a payload, THE ExotelProvider
   SHALL set `ProviderEvent.type = "dtmf"` and
   `ProviderEvent.data = {"digits": body["Digits"]}`.
2. WHEN the `Digits` field is absent or empty, THE ExotelProvider SHALL still set
   `ProviderEvent.type = "dtmf"` with `data = {"digits": ""}` so the flow engine
   can treat it as a timeout/no-input.

---

### Requirement 6: Webhook Parsing — Recording Endpoint

**User Story:** As the webhook handler, I want the recording endpoint to correctly
parse Exotel's recording-ready callback, so that completed recordings are downloaded
and stored for speech classification.

#### Acceptance Criteria

1. WHEN the `/webhooks/{secret}/recording` endpoint receives a payload, THE
   ExotelProvider SHALL set `ProviderEvent.type = "recording_ready"` and
   `ProviderEvent.data = {"recording_url": body["RecordingUrl"]}`.
2. WHEN the `RecordingUrl` field is absent or empty, THE ExotelProvider SHALL set
   `data = {"recording_url": ""}` and log a warning at `WARNING` level with the key
   `exotel_recording_url_missing`.

---

### Requirement 7: Call Flow Rendering

**User Story:** As the flow engine, I want `render_steps` to return a response body
in the exact format Exotel's dynamic-mode Flow URL expects, so that Exotel can execute
the correct call actions (play audio, gather digits, record speech, hang up) when it
fetches the flow URL.

#### Acceptance Criteria

1. WHEN `render_steps` is called with a `Play` step, THE ExotelProvider SHALL include
   a node `{"action": "play", "url": audio_url}` in the response.
2. WHEN `render_steps` is called with a `Gather` step, THE ExotelProvider SHALL include
   a node with `"action": "gather"`, `"maxDigits": max_digits`,
   `"timeoutMs": timeout_sec * 1000`, and, when `prompt_audio_url` is non-empty,
   `"playUrl": prompt_audio_url`.
3. WHEN `render_steps` is called with a `Record` step, THE ExotelProvider SHALL include
   a node with `"action": "record"`, `"maxLength": max_seconds`,
   `"silenceTimeout": silence_timeout_sec`, and `"playBeep": play_beep`.
4. WHEN `render_steps` is called with a `Hangup` step, THE ExotelProvider SHALL include
   a node `{"action": "hangup"}`.
5. THE ExotelProvider SHALL wrap all rendered nodes in a top-level `"flow"` key:
   `{"flow": [...]}`.
6. THE ExotelProvider SHALL return the rendered response as a `fastapi.responses.JSONResponse`
   so that the webhook router can return it directly as the HTTP response to Exotel.
7. WHEN `render_steps` is called with an empty list, THE ExotelProvider SHALL return
   `{"flow": []}`.

---

### Requirement 8: Recording Download

**User Story:** As the recordings task, I want `fetch_recording` to download a call
recording from the Exotel-provided URL using authenticated HTTP, so that the recording
can be stored and used for speech classification.

#### Acceptance Criteria

1. WHEN `fetch_recording` is called with a URL, THE ExotelProvider SHALL send an HTTP
   GET to that URL with HTTP Basic Auth (API key / token).
2. WHEN the download succeeds, THE ExotelProvider SHALL write the response bytes to the
   `dest` path (creating parent directories if needed) and return the `dest` path.
3. IF the download fails with an HTTP or network error, THEN THE ExotelProvider SHALL
   raise the error so the `telephony.fetch_recording` Celery task can retry.
4. THE ExotelProvider SHALL use a 30-second timeout for recording downloads to
   accommodate large audio files.

---

### Requirement 9: Startup Configuration Validation

**User Story:** As a developer configuring the system, I want the application to fail
fast with a clear error message if required Exotel credentials are missing when
`CALL_PROVIDER=exotel`, so that misconfiguration is caught at startup rather than at
call time.

#### Acceptance Criteria

1. WHEN `CALL_PROVIDER=exotel` and any of `EXOTEL_API_KEY`, `EXOTEL_API_TOKEN`, or
   `EXOTEL_SID` is blank or a placeholder value, THE Config_Validator SHALL raise a
   `ValueError` at application startup with a message listing each missing variable.
2. WHEN `CALL_PROVIDER=exotel` and `PUBLIC_BASE_URL` is `"http://localhost:8000"` or
   does not begin with `"https://"`, THE Config_Validator SHALL log a warning at
   `WARNING` level with the key `exotel_public_url_not_https` explaining that Exotel
   requires a public HTTPS callback URL.
3. WHEN `CALL_PROVIDER=mock` or `CALL_PROVIDER=auto`, THE Config_Validator SHALL NOT
   raise an error if Exotel credentials are absent; the factory will silently fall
   back to MockProvider.
4. WHEN `CALL_PROVIDER=exotel` and `EXOTEL_CALLER_ID` is blank, THE Config_Validator
   SHALL raise a `ValueError` at startup, because every outbound call requires a
   caller ID.
5. WHEN all required credentials are present and valid, THE Config_Validator SHALL log
   a single INFO-level message with the key `exotel_config_ok` listing the SID
   (not the key or token) and the subdomain.

---

### Requirement 10: Provider Auto-Selection

**User Story:** As an operator, I want the factory to automatically select ExotelProvider
when all Exotel credentials are present in the environment, so that setting
`CALL_PROVIDER=auto` in production requires no other code changes.

#### Acceptance Criteria

1. WHEN `CALL_PROVIDER=exotel` and all of `EXOTEL_API_KEY`, `EXOTEL_API_TOKEN`, and
   `EXOTEL_SID` are non-empty, non-placeholder values, THE Factory SHALL return an
   `ExotelProvider` instance.
2. WHEN `CALL_PROVIDER=auto` and all Exotel credentials are present, THE Factory SHALL
   return an `ExotelProvider` instance.
3. WHEN `CALL_PROVIDER=auto` and Exotel credentials are absent or partial, THE Factory
   SHALL return a `MockProvider` instance without raising an error.
4. WHEN `CALL_PROVIDER=mock`, THE Factory SHALL always return a `MockProvider`
   instance regardless of whether Exotel credentials are present.
5. THE Factory SHALL consider a credential invalid if it is empty, begins with
   `"your-"`, begins with `"change-"`, contains `"example"`, or equals `"placeholder"`
   (case-insensitive), consistent with the existing `_is_valid_cred` helper.

---

### Requirement 11: Webhook URL Construction

**User Story:** As the call scheduler, I want the webhook URLs embedded in each
`PlaceCallRequest` to be correctly formed so that Exotel can reach the backend's
callback endpoints from the public internet.

#### Acceptance Criteria

1. WHEN a `PlaceCallRequest` is constructed for an Exotel call, THE Scheduler SHALL
   set `flow_url` to `{PUBLIC_BASE_URL}/webhooks/{WEBHOOK_SECRET}/flow`.
2. WHEN a `PlaceCallRequest` is constructed for an Exotel call, THE Scheduler SHALL
   set `status_callback_url` to `{PUBLIC_BASE_URL}/webhooks/{WEBHOOK_SECRET}/status`.
3. THE Scheduler SHALL append the `call_id` as a query parameter to the `flow_url`
   so that it is available to the webhook handler via `request.query_params`:
   `{PUBLIC_BASE_URL}/webhooks/{WEBHOOK_SECRET}/flow?call_id={call_id}`.
4. THE Scheduler SHALL NOT include the `call_id` query parameter in the
   `status_callback_url`; the `call_id` is recovered there via the `CustomField`
   in the Exotel POST body.
5. WHEN `PUBLIC_BASE_URL` contains a trailing slash, THE Scheduler SHALL strip it
   before constructing the webhook URLs.

---

### Requirement 12: Idempotent Webhook Processing

**User Story:** As the webhook handler, I want duplicate Exotel webhook deliveries to
be safely ignored, so that network retries from Exotel do not cause double-processing
of events.

#### Acceptance Criteria

1. THE ExotelProvider SHALL compute an idempotency key for every `ProviderEvent` using
   the `make_idempotency_key` helper from `base.py` with `provider="exotel"`.
2. THE ExotelProvider SHALL include in the stable-fields string the `Status` value and
   the `StartTime` (or `DateCreated`) timestamp from the Exotel payload so that the
   same event from the same call always produces the same key.
3. WHEN two webhook deliveries for the same call SID and event type carry identical
   stable fields, THE ExotelProvider SHALL produce identical idempotency keys for both.
4. WHEN two webhook deliveries for the same call SID have different `Status` values
   (e.g. `"ringing"` then `"completed"`), THE ExotelProvider SHALL produce different
   idempotency keys for each.

---

### Requirement 13: Logging and Observability

**User Story:** As a developer debugging a production call, I want consistent structured
log entries from ExotelProvider, so that I can trace the full call lifecycle without
exposing sensitive data.

#### Acceptance Criteria

1. WHEN `place_call` completes successfully, THE ExotelProvider SHALL log at `INFO`
   level with the keys `call_id`, `sid`, and `raw_status` (never the destination
   phone number or credentials).
2. WHEN `parse_webhook` is called, THE ExotelProvider SHALL NOT log the full webhook
   body; it SHALL log only `kind`, `event_type`, `sid`, and `phone_last4` (last 4
   digits of the `To` field if present).
3. WHEN any HTTP request to the Exotel API fails, THE ExotelProvider SHALL log the
   HTTP status code and the error message at `ERROR` level with the key
   `exotel_api_error` before re-raising.
4. THE ExotelProvider SHALL use the `structlog` logger (consistent with the rest of
   the codebase) and SHALL NOT use Python's built-in `logging` module directly.

---

### Requirement 14: Mock Provider Isolation

**User Story:** As a developer without Exotel credentials, I want the MockProvider to
continue working exactly as before, so that local development and CI tests are unaffected
by the Exotel integration work.

#### Acceptance Criteria

1. WHEN `CALL_PROVIDER=mock`, THE Factory SHALL return a `MockProvider` instance and
   SHALL NOT instantiate `ExotelProvider`.
2. THE MockProvider SHALL NOT be modified as part of this integration; all Exotel
   logic is confined to `ExotelProvider` and `Config_Validator`.
3. WHEN `CALL_PROVIDER=auto` and Exotel credentials are absent, THE Factory SHALL
   return a `MockProvider` without logging any error (only a debug-level log is
   acceptable).
4. THE MockProvider's `render_steps` and `parse_webhook` methods SHALL continue to
   return the same JSON structures they currently return, unchanged.

---

### Requirement 15: Audio Format Compatibility

**User Story:** As a call recipient, I want audio played during my call to use the
correct format for Exotel, so that the audio is intelligible without distortion or
silence.

#### Acceptance Criteria

1. THE ExotelProvider's `render_steps` method SHALL reference audio URLs as returned by
   the flow engine (pointing to `{PUBLIC_BASE_URL}/media/audio/{sha256}.wav`) without
   transcoding; the audio pipeline (TTS → `audio_assets` table) already produces
   WAV 8 kHz mono PCM16 files which match the Exotel-required format per
   CONTRACTS.md section 8.3.
2. WHERE a `Gather` step has a non-null `prompt_audio_url`, THE ExotelProvider SHALL
   include it as `"playUrl"` in the rendered gather node, so that Exotel plays the
   prompt before collecting digits.
3. THE ExotelProvider SHALL NOT modify audio URLs (no re-signing, no transcoding
   parameters); the URL is served publicly as-is.

