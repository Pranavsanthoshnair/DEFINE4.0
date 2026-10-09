# Design Document: Exotel Integration

## Overview

This document describes the surgical changes required to make `ExotelProvider` production-ready.
The platform already has a complete provider abstraction, a working `MockProvider`, a webhook
router, a flow engine, and a factory that auto-selects a provider from environment variables.
The work here is a set of targeted edits to five existing files plus one new test file.

**No new modules are introduced.** Every change is confined to:

| File | Nature of change |
|---|---|
| `backend/app/telephony/providers/exotel.py` | Fix gaps in hangup, render_steps, parse_webhook, place_call |
| `backend/app/telephony/providers/factory.py` | Add `validate_exotel_config()` |
| `backend/app/telephony/scheduler.py` | Fix webhook URL construction |
| `backend/app/main.py` | Add startup lifespan call to `validate_exotel_config()` |
| `backend/tests/telephony/test_exotel_provider.py` | New test file |

---

## Architecture

The integration plugs into the existing provider abstraction without changing any interfaces.

```
┌─────────────────────────────────────────────────────────────┐
│ Application Startup (main.py lifespan)                      │
│   └─ validate_exotel_config()  [factory.py]                 │
│       ├─ raises ValueError if creds missing/invalid        │
│       └─ logs warning if PUBLIC_BASE_URL not HTTPS          │
└─────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ Call Placement (scheduler.py → tasks.py → ExotelProvider.place_call)       │
│                                                                            │
│  scheduler.execute_place_call()                                            │
│    ├─ flow_url    = {PUBLIC_BASE_URL.rstrip('/')}/webhooks/{SECRET}/flow   │
│    │               ?call_id={call_id}                                      │
│    ├─ status_url  = {PUBLIC_BASE_URL.rstrip('/')}/webhooks/{SECRET}/status │
│    │               (no call_id — recovered from CustomField)               │
│    └─ ExotelProvider.place_call(PlaceCallRequest)                          │
│         └─ POST https://{EXOTEL_SUBDOMAIN}/v1/Accounts/{SID}/Calls/        │
│                connect.json  (Basic Auth, 10s timeout)                     │
└────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ Webhook Pipeline (webhooks.py — unchanged)                               │
│                                                                          │
│  POST /webhooks/{secret}/flow         → ExotelProvider.parse_webhook     │
│  POST /webhooks/{secret}/status       → ExotelProvider.parse_webhook     │
│  POST /webhooks/{secret}/input        → ExotelProvider.parse_webhook     │
│  POST /webhooks/{secret}/recording    → ExotelProvider.parse_webhook     │
│                                                                          │
│  For "flow" kind:                                                        │
│    decision = flow_next(ctx, flow_event)                                 │
│    rendered = provider.render_steps(decision.steps)                      │
│    ├─ if isinstance(rendered, dict): return JSONResponse(content=rendered)│
│    └─ return rendered   ← ExotelProvider returns JSONResponse directly   │
└──────────────────────────────────────────────────────────────────────────┘
```

### Key design decisions

**`render_steps` returns `JSONResponse`, not `dict`.**  
The webhook handler already handles both paths:  
```python
if isinstance(rendered, dict):
    return JSONResponse(content=rendered)
return rendered
```
`ExotelProvider.render_steps` returns a `JSONResponse` directly. `MockProvider` returns a
`dict` — this is intentional and unchanged.

**`validate_exotel_config()` lives in `factory.py`, not a new module.**  
It reuses `_is_valid_cred()` which already encodes the placeholder-detection logic. Keeping
related credential logic together minimises duplication.

**`hangup` uses `Status="completed"`, not `"canceled"`.**  
The existing stub sends `"canceled"`. Requirement 2.1 specifies `"completed"`.
This is a one-line fix.

**`status_callback_url` does not carry `call_id`.**  
The existing `scheduler.py` appends `?call_id={call_id}` to both URLs. Requirement 11.4
specifies the status URL should not carry it — `call_id` is recovered there from
`CustomField` in Exotel's POST body. This is a one-line fix.

**Exotel API base URL construction — one VERIFY item remains.**  
The current stub constructs:
```
https://{subdomain}.api.exotel.com/v1/Accounts/{SID}
```
The requirements show:
```
https://{EXOTEL_SUBDOMAIN}/v1/Accounts/{EXOTEL_SID}
```
where `EXOTEL_SUBDOMAIN` appears to be a full hostname like `api.exotel.in`. The design
follows the requirements verbatim (`https://{settings.exotel_subdomain}/v1/Accounts/{self._sid}`).
If the actual Exotel account uses a compound subdomain, only the `_base_url` assignment
in `__init__` needs updating.

---

## Components and Interfaces

### ExotelProvider (exotel.py)

All changes are surgical — no structural changes to the class.

#### `__init__` — fix base URL

```python
self._base_url = f"https://{settings.exotel_subdomain}/v1/Accounts/{self._sid}"
```
Previously appended `.api.exotel.com` which may be incorrect.

#### `place_call` — add no-SID warning branch

```python
if not sid:
    log.warning("exotel_place_call_no_sid", call_id=str(req.call_id), raw_status=raw_status)
return PlaceCallResult(
    provider_call_sid=sid,
    accepted=bool(sid),
    raw_status=raw_status,
)
```

#### `hangup` — fix Status field + add try/except

```python
async def hangup(self, provider_call_sid: str) -> None:
    try:
        async with httpx.AsyncClient(auth=self._auth, timeout=5.0) as client:
            resp = await client.post(
                f"{self._base_url}/Calls/{provider_call_sid}.json",
                data={"Status": "completed"},   # was "canceled"
            )
            resp.raise_for_status()
    except Exception as exc:
        log.warning("exotel_hangup_failed", sid=provider_call_sid, error=str(exc))
```

#### `parse_webhook` — add phone_last4 log + missing-RecordingUrl warning

```python
phone_last4 = str(body.get(_FIELD_TO, ""))[-4:] or ""
log.info("exotel_webhook", kind=kind, event_type=event_type, sid=sid, phone_last4=phone_last4)
# ...
elif kind == "recording":
    event_type = "recording_ready"
    rec_url = body.get(_FIELD_RECORDING_URL, "")
    if not rec_url:
        log.warning("exotel_recording_url_missing", sid=sid)
    data = {"recording_url": rec_url}
```

#### `render_steps` — return JSONResponse

```python
from fastapi.responses import JSONResponse

def render_steps(self, steps: list[CallStep]) -> JSONResponse:
    # ... build rendered list ...
    return JSONResponse(content={"flow": rendered})
```

### validate_exotel_config (factory.py)

New function, called from `main.py` lifespan:

```python
def validate_exotel_config() -> None:
    """
    Validate that all required Exotel credentials are present.
    Only runs when CALL_PROVIDER=exotel.
    Raises ValueError listing missing vars.
    Logs WARNING if PUBLIC_BASE_URL is not HTTPS.
    Logs INFO exotel_config_ok on success.
    """
    if settings.call_provider.lower() != "exotel":
        return

    required = {
        "EXOTEL_API_KEY": settings.exotel_api_key,
        "EXOTEL_API_TOKEN": settings.exotel_api_token,
        "EXOTEL_SID": settings.exotel_sid,
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

    log.info(
        "exotel_config_ok",
        sid=settings.exotel_sid,
        subdomain=settings.exotel_subdomain,
    )
```

### Webhook URL fix (scheduler.py)

In `execute_place_call`:

```python
base = settings.public_base_url.rstrip("/")
secret = settings.webhook_secret

flow_url = f"{base}/webhooks/{secret}/flow?call_id={call_id}"
status_callback_url = f"{base}/webhooks/{secret}/status"
```

### Startup hook (main.py)

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    if settings.call_provider.lower() == "exotel":
        from app.telephony.providers.factory import validate_exotel_config
        validate_exotel_config()
    log.info("veylo_api_started", env=settings.environment)
    yield
```

---

## Data Models

No new models. Existing types from `base.py` remain unchanged:

| Type | Role |
|---|---|
| `PlaceCallRequest` | Input to `place_call`: call_id, to_number, caller_id, flow_url, status_callback_url, custom_field, time_limit_sec |
| `PlaceCallResult` | Output of `place_call`: provider_call_sid, accepted, raw_status |
| `ProviderEvent` | Normalised webhook event: type, provider_call_sid, call_id, data, idempotency_key |
| `CallStep` | Union of `Play | Gather | Record | Hangup` — input to `render_steps` |

### Idempotency key construction

```
sha256("exotel" | provider_call_sid | event_type | json.dumps({"status": raw_status, "ts": timestamp}, sort_keys=True))
```

`raw_status` and `ts` (StartTime or DateCreated from Exotel payload) are the stable fields that
distinguish events from the same call. Two identical deliveries of the same event produce the
same key; a `ringing` callback and a `completed` callback for the same SID produce different keys
because `raw_status` differs.

### Status mapping table

| Exotel `Status` | `ProviderEvent.type` | `data` |
|---|---|---|
| `ringing` | `ringing` | `{}` |
| `in-progress` | `answered` | `{}` |
| `completed` | `completed` | `{"status": "completed", "duration": int, "hangup_cause": str}` |
| `busy` | `busy` | `{"status": "busy", "duration": 0, "hangup_cause": ""}` |
| `no-answer` | `no_answer` | `{"status": "no_answer", "duration": 0, "hangup_cause": ""}` |
| `failed` / `canceled` / absent / unknown | `failed` | `{"status": "failed", "duration": 0, "hangup_cause": "unknown"}` |

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions
of a system — essentially, a formal statement about what the system should do. Properties serve
as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: parse_webhook always produces a non-empty idempotency key

*For any* valid Exotel webhook payload across all four endpoint kinds (`flow`, `status`, `input`,
`recording`), `parse_webhook` must return a `ProviderEvent` whose `idempotency_key` is a
non-empty string.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 5.1, 6.1, 12.1, 12.2**

---

### Property 2: render_steps produces a JSONResponse with a "flow" key of matching length

*For any* list of `CallStep` objects (including the empty list), `render_steps` must return a
`fastapi.responses.JSONResponse` whose decoded body contains a `"flow"` key whose value is a
list of exactly the same length as the input.

**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7**

---

### Property 3: parse_webhook is deterministic — identical payloads produce identical idempotency keys

*For any* webhook payload, calling `parse_webhook` twice with the same arguments must produce
`ProviderEvent` values with identical `idempotency_key` fields.

**Validates: Requirements 12.3**

---

### Property 4: parse_webhook is sensitive to Status — payloads differing only in Status produce different idempotency keys

*For any* two webhook payloads that are identical except their `Status` fields differ (e.g.
`"ringing"` vs `"completed"`), `parse_webhook` must produce `ProviderEvent` values with
distinct `idempotency_key` fields.

**Validates: Requirements 12.4**

---

### Property 5: validate_exotel_config raises ValueError for any combination of missing required credentials

*For any* subset of the four required variables (`EXOTEL_API_KEY`, `EXOTEL_API_TOKEN`,
`EXOTEL_SID`, `EXOTEL_CALLER_ID`) that is blank or a placeholder, when `CALL_PROVIDER=exotel`,
`validate_exotel_config()` must raise a `ValueError` whose message lists every missing variable
name.

**Validates: Requirements 9.1, 9.4**

---

### Property 6: Webhook URL construction strips trailing slashes and correctly places call_id

*For any* `PUBLIC_BASE_URL` value (with or without trailing slash) and any `call_id` UUID,
the constructed `flow_url` must end with `/flow?call_id={call_id}` and
`status_callback_url` must end with `/status` (without a `call_id` parameter).

**Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5**

---

## Error Handling

### place_call errors

| Condition | Handling |
|---|---|
| Exotel returns 4xx / 5xx | `resp.raise_for_status()` propagates `httpx.HTTPStatusError` — Celery task retries |
| Network timeout / connection error | `httpx.TimeoutException` propagates — Celery task retries |
| 2xx but empty `CallSid` | `accepted=False`, `WARNING` log with `exotel_place_call_no_sid` |

### hangup errors

| Condition | Handling |
|---|---|
| Any HTTP or network error | Caught, `WARNING` log, return without raising — sweep task must not crash |

### parse_webhook errors

| Condition | Handling |
|---|---|
| Invalid UUID in `CustomField` | `call_id = None` (event still processed, idempotency key still valid) |
| Missing `RecordingUrl` | `recording_url = ""`, `WARNING` log with `exotel_recording_url_missing` |
| Unknown `Status` value | Maps to `"failed"` event type |

### validate_exotel_config errors

| Condition | Handling |
|---|---|
| Missing/placeholder creds with `CALL_PROVIDER=exotel` | Raises `ValueError` — application refuses to start |
| Non-HTTPS `PUBLIC_BASE_URL` | `WARNING` log, no exception — developer may intentionally use HTTP for tunnelled dev |

### fetch_recording errors

| Condition | Handling |
|---|---|
| Any HTTP or network error | Propagates — `telephony.fetch_recording` Celery task retries up to 3 times |

---

## Testing Strategy

### Dual testing approach

Unit tests cover specific examples, edge cases, and error conditions. Property tests (using
**Hypothesis**) validate universal correctness guarantees across generated inputs.

`hypothesis` is not yet in `requirements.txt`. Add it:
```
hypothesis>=6.100.0
```

### Test file layout

All tests live in `backend/tests/telephony/test_exotel_provider.py`.
HTTP calls are mocked with **respx** (already in `requirements.txt` as `respx>=0.21.0`).

### Unit test coverage

| Test | Requirement(s) |
|---|---|
| `test_parse_webhook_flow_answered` — no AMD, no Digits → answered | Req 3.5 |
| `test_parse_webhook_flow_amd_result` — AmdResult present → amd_result | Req 3.3 |
| `test_parse_webhook_flow_dtmf` — Digits present, no AmdResult → dtmf | Req 3.4 |
| `test_parse_webhook_status_completed` — Status=completed | Req 4.3 |
| `test_parse_webhook_status_no_answer` — Status=no-answer | Req 4.5 |
| `test_parse_webhook_status_failed` — Status=failed / absent | Req 4.6 |
| `test_parse_webhook_input` — kind=input, Digits present and absent | Req 5.1–5.2 |
| `test_parse_webhook_recording` — RecordingUrl present | Req 6.1 |
| `test_parse_webhook_recording_missing_url` — absent RecordingUrl → warning | Req 6.2 |
| `test_render_steps_play` — Play step | Req 7.1 |
| `test_render_steps_gather_with_prompt` — Gather with prompt_audio_url | Req 7.2 |
| `test_render_steps_gather_no_prompt` — Gather without prompt | Req 7.2 |
| `test_render_steps_record` — Record step | Req 7.3 |
| `test_render_steps_hangup` — Hangup step | Req 7.4 |
| `test_render_steps_empty` — empty list → {"flow": []} | Req 7.7 |
| `test_render_steps_returns_json_response` — return type | Req 7.6 |
| `test_validate_config_raises_missing_key` — blank API_KEY | Req 9.1 |
| `test_validate_config_raises_missing_caller_id` — blank CALLER_ID | Req 9.4 |
| `test_validate_config_warns_non_https` — http:// URL | Req 9.2 |
| `test_validate_config_ok_logs_info` — all creds valid | Req 9.5 |
| `test_validate_config_skips_when_mock` — CALL_PROVIDER=mock | Req 9.3 |
| `test_place_call_no_sid_warning` — 2xx but empty CallSid → accepted=False | Req 1.6 |
| `test_hangup_swallows_http_error` — hangup error does not raise | Req 2.3 |
| `test_hangup_uses_completed_status` — Status field is "completed" | Req 2.1 |

### Property test coverage

Each property test runs minimum **100 iterations** via Hypothesis `@settings(max_examples=100)`.

| Property test | Property # | Hypothesis strategy |
|---|---|---|
| `test_prop_parse_webhook_ikey_nonempty` | Property 1 | `st.one_of(...)` over all 4 kinds with `st.text()`/`st.uuids()` fields |
| `test_prop_render_steps_flow_length` | Property 2 | `st.lists(st.one_of(Play, Gather, Record, Hangup))` |
| `test_prop_ikey_deterministic` | Property 3 | Same payload generated twice, assert equal keys |
| `test_prop_ikey_status_sensitive` | Property 4 | Two payloads differing only in Status, assert different keys |
| `test_prop_validate_config_missing_creds` | Property 5 | `st.sets(st.sampled_from([...]))` of missing cred subsets |
| `test_prop_webhook_url_construction` | Property 6 | `st.uuids()` × `st.text()` base URLs with/without trailing slash |

Tag format for each property test:
```python
# Feature: exotel-integration, Property N: <property text>
```

### No real network calls

All `httpx.AsyncClient` calls in `ExotelProvider` are intercepted with `respx.mock`.
`validate_exotel_config` has no network calls.
`render_steps` and `parse_webhook` are pure functions — no mocking needed.
