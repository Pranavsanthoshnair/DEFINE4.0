# PR 002 — Shared Contracts (v1.0)

This file is the single source of truth for everything two or more members depend on: repo layout, naming, database schema, REST API, AI service API, telephony interfaces, state machine, task names, environment variables and ports.

**Rules for using this file**

1. Build against it exactly. If something here is ambiguous or wrong, do not guess. Open a PR that edits this file, label it `contract-change`, and announce it in the team chat. Merge only after the owner of the affected section approves.
2. Section owners: sections 4 and 6 belong to Member 1, sections 7 to 8 are split as marked, section 9 belongs to Member 2, section 12 belongs to Member 4.
3. Anything marked **VERIFY AT KICKOFF** depends on Exotel behaviour we cannot confirm until we have sandbox access. Code against the abstraction, not against the guess.

---

## 1. Repository layout and ownership

Monorepo `pr002/`. Each member edits only their own directories. Cross-boundary edits go through a PR reviewed by the owner.

```
DEFINE4.0/                        # repo root
  docker-compose.yml               # M4
  .env.example                     # M4 (every member adds their own vars via PR)
  Makefile                         # M4
  docs/
    PRD.md                         # shared
    CONTRACTS.md                   # shared
    PRIVACY.md                     # M1
    CALLING_APPROACH.md            # M2
    MODEL_REPORT.md                # M3
    DEMO.md                        # M4
    members/                       # the four member docs
  backend/                         # FastAPI app + Celery worker (same image) — M1 & M2
    app/
      main.py                      # M1 (mounts all routers)
      config.py                    # M1
      celery_app.py                # M1
      db/                          # M1: models.py, session.py, migrations/ (Alembic)
      security/                    # M1: crypto.py, auth.py, audit.py
      campaigns/                   # M1: router.py, service.py, csv_import.py, prepare.py, schemas.py
      templates/                   # M1: router.py, service.py, schemas.py, presets/*.json
      analytics/                   # M1: router.py, queries.py
      telephony/                   # M2: providers/, flow/, webhooks.py, scheduler.py, tasks.py, retry.py, recordings.py
      ai_client/                   # M1 writes the typed client for the AI service; M3 reviews
    tests/
      telephony/                   # M2 telephony tests
    requirements.txt
    pytest.ini
    pyrightconfig.json
  ai/                              # M3: AI service (separate image)
    app/
      main.py, config.py, schemas.py
      audio/                       # M3: io.py, resample.py, vad.py
      stt/                         # M3: base.py, faster_whisper_engine.py, indic_conformer_engine.py, router.py
      intent/                      # M3: rules.py, model.py, llm_fallback.py, pipeline.py, lexicon/
      translate/                   # M3: indictrans.py, llm_fallback.py, placeholders.py
      tts/                         # M3: edge.py, parler.py, postprocess.py
    ml/                            # M3: dataset generation, training, export, benchmarks
      intent/                      # generate_data.py, build_dataset.py, train.py, evaluate.py, export_onnx.py
      stt_benchmark/               # prepare_clips.py, run_benchmark.py, results/
    tests/
    Dockerfile, pyproject.toml, models.yaml, pytest.ini
  frontend/                        # M4: Next.js dashboard
    src/
      app/
        layout.tsx, page.tsx       # root layout and home/overview
        login/                     # M4: login page
        templates/                 # M4: list page + [id]/ (detail/translation editor)
        campaigns/                 # M4: list page, new/ (wizard), [id]/ (dashboard)
        analytics/                 # M4: analytics overview
        contacts/                  # M4: contacts table
        dashboard/                 # M4: overview redirect
        privacy/                   # M4: processing-location statement page
      components/
        layout/                    # M4: sidebar, header, shell
        ui/                        # M4: shadcn/ui wrappers
        campaigns/                 # M4: wizard steps, retry modal, call detail drawer
        charts/                    # M4: outcome charts, breakdowns
      hooks/                       # M4: useApi.ts and other custom hooks
      lib/                         # M4: api-client.ts, supabase.ts, utils.ts
      types/                       # M4: shared TypeScript types
    mocks/                         # M4: MSW handlers for every contract route
    public/
  infra/                           # M4: Caddy snippet, backup scripts, deploy scripts
    caddy/pr002.caddy
    backup/pg_backup.sh, restore_test.sh
    deploy/deploy.sh, bootstrap_vps.md
  fixtures/                        # shared: sample CSVs, templates, test audio
    contacts_sample.csv
    template_seminar.json
    audio/                         # M3: yes/no/noise wav clips per language
    exotel/                        # M2: sanitised real webhook payload samples
```

Git workflow: `main` is protected and always deployable. Feature branches named `m<N>/<short-topic>`. One PR per task, reviewed by one other member. Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`). Squash merge.

---

## 2. Conventions

| Topic | Rule |
|---|---|
| IDs | UUID v4, generated in the application, stored as `uuid`. |
| Timestamps | `timestamptz`, always UTC in the database and in JSON (ISO 8601 with `Z`). Convert to IST only for the calling-window check and for display in the UI. |
| Phone numbers | E.164 (`+919876543210`). Input without a country code and 10 digits long is treated as India (`+91`). |
| Language codes | ISO 639-1 lowercase: `en`, `hi`, `ml`, `ta`, `te`, `kn`, `bn`, `mr`, `gu`. Demo set is `en`, `hi`, `ml`, `ta`. |
| JSON naming | `snake_case` everywhere (database, API, internal calls). |
| API base paths | `/api/...` authenticated REST. `/webhooks/...` provider callbacks. `/media/...` public audio. `/healthz` on every service. |
| Error format | `{"error": {"code": "string_code", "message": "human readable", "details": {}}}` with a correct HTTP status. |
| Pagination | Query `page` (from 1) and `page_size` (default 25, max 100). Response `{"items": [], "page": 1, "page_size": 25, "total": 0}`. |
| Auth | `Authorization: Bearer <JWT>`. HS256. Expiry 12 hours. Roles: `admin`, `organiser`. |
| Python | 3.12, type hints required, `ruff` + `ruff format`, `pytest`. |
| Node | 20 LTS, TypeScript strict. |
| Logging | `structlog` JSON to stdout. Never log phone numbers, names, transcripts or recording URLs in full. Log `contact_id`, `call_id`, and `phone_last4` only. |

---

## 3. Enums (use these exact string values)

```
campaign.status:           draft | preparing | needs_review | ready | running | paused | completed | cancelled
campaign_contact.state:    pending | in_call | waiting_retry | done | exhausted | skipped
call.status:               initiated | ringing | in_progress | completed | failed | busy | no_answer | canceled
outcome:                   pending | confirmed | declined | reschedule | call_later | unclear
                           | no_answer | busy | voicemail | failed | no_input | opted_out
intent:                    confirm | decline | reschedule | call_later | stop_calling | unclear
intent.source:             dtmf | speech
amd_result:                human | machine | unknown
translation.status:        draft | approved
voicemail_policy:          leave_message | skip_and_retry
user.role:                 admin | organiser
use_case:                  seminar | clinic | school | payment | custom
```

Intent to outcome mapping: `confirm→confirmed`, `decline→declined`, `reschedule→reschedule`, `call_later→call_later`, `stop_calling→opted_out`, `unclear→unclear`.

Retry sets:

```
RETRYABLE_OUTCOMES   = {no_answer, busy, voicemail, no_input, unclear, failed, call_later}
NON_RESPONDER_SET    = {no_answer, busy, voicemail, no_input}      # default for the dashboard "Retry non-responders" button
TERMINAL_OUTCOMES    = {confirmed, declined, reschedule, opted_out}
```

---

## 4. Database schema (owner: Member 1)

PostgreSQL 16. SQLAlchemy 2.0 models in `backend/app/db/models.py`. Alembic migrations in `backend/app/db/migrations/`. Column names below are final.

### users
`id uuid pk`, `email text unique not null`, `password_hash text not null` (argon2), `role text not null`, `created_at timestamptz`.

### contacts
| column | type | notes |
|---|---|---|
| id | uuid pk | |
| phone_enc | bytea not null | AES-256-GCM, format `nonce(12) \|\| ciphertext+tag` |
| phone_hash | char(64) not null unique | HMAC-SHA256 hex of the E.164 number with `PHONE_HMAC_KEY`. Used for dedupe and lookup. |
| phone_last4 | char(4) not null | for display and logs |
| name_enc | bytea null | same encryption as phone |
| language | char(2) not null | |
| segment | text null | free text from the CSV, for example `students` |
| consent | boolean not null default false | |
| consent_source | text null | for example `csv_import` |
| consent_at | timestamptz null | |
| dnd | boolean not null default false | |
| opted_out | boolean not null default false | set when the person says or presses stop |
| opted_out_at | timestamptz null | |
| created_at | timestamptz | |

### templates
`id`, `name text`, `use_case text`, `source_language char(2) default 'en'`, `variables jsonb` (list of `{key,label,required}`), `script jsonb` (segments in the source language, see section 5), `dtmf_map jsonb` (for example `{"1":"confirm","2":"decline","3":"reschedule","9":"stop_calling"}`), `speech_enabled boolean`, `voicemail_policy text`, `is_preset boolean`, `created_by uuid`, `created_at`.

### template_translations
`id`, `template_id fk`, `language char(2)`, `segments jsonb` (same keys as `templates.script`, still containing `{placeholders}`), `status text` (`draft|approved`), `source text` (`ai|manual`), `approved_by uuid null`, `approved_at null`, `created_at`. Unique `(template_id, language)`.

### campaigns
`id`, `name`, `template_id fk`, `status text`, `event_details jsonb` (values for the template variables, for example `{"event_name":"AI Workshop","date":"12 October","venue":"Main Auditorium"}`), `variable_overrides jsonb` (optional per-language overrides: `{"hi":{"date":"12 अक्टूबर"}}`), `languages text[]`, `caller_id text` (ExoPhone number), `calling_window_start time default '09:00'`, `calling_window_end time default '21:00'`, `timezone text default 'Asia/Kolkata'`, `max_attempts int default 3`, `max_concurrent_calls int default 3`, `retry_policy jsonb` (default in section 9.4), `speech_confidence_threshold float default 0.6`, `created_by`, `created_at`, `launched_at null`, `completed_at null`.

### audio_assets
`id`, `campaign_id fk`, `language char(2)`, `segment_key text`, `text text` (final spoken text), `sha256 char(64)`, `wav_path text` (relative to `MEDIA_DIR`), `duration_ms int`, `created_at`. Unique `(campaign_id, language, segment_key)`. Public URL: `{PUBLIC_BASE_URL}/media/audio/{sha256}.wav`.

### campaign_contacts
`id`, `campaign_id fk`, `contact_id fk null` (`ON DELETE SET NULL`, so erasure keeps statistics), `language char(2)` (copied from the contact at enqueue time), `segment text null` (copied), `state text`, `attempts int default 0`, `max_attempts_override int null`, `next_attempt_at timestamptz null`, `last_outcome text null`, `final_outcome text null`, `last_call_at null`, `created_at`. Unique `(campaign_id, contact_id)`. Index on `(campaign_id, state, next_attempt_at)`.

### calls
`id`, `campaign_contact_id fk`, `attempt_no int`, `provider text` (`exotel|mock`), `provider_call_sid text unique null`, `status text`, `outcome text null`, `amd_result text null`, `flow_step text null`, `flow_state jsonb default '{}'` (see 9.2), `started_at`, `answered_at null`, `ended_at null`, `duration_sec int null`, `hangup_cause text null`, `recording_path text null` (encrypted file, relative to `RECORDINGS_DIR`), `recording_provider_url text null`, `created_at`.

### call_events
`id bigserial pk`, `call_id uuid null`, `provider_call_sid text null`, `event_type text`, `payload jsonb` (raw provider payload with phone numbers masked to last 4), `idempotency_key text unique not null`, `received_at timestamptz`.

### intents
`id`, `call_id fk`, `step_key text`, `source text`, `raw_input text` (the digit, or the transcript), `language char(2)`, `label text`, `confidence float`, `stt_model text null`, `latency_ms int null`, `created_at`.

### audit_log
`id bigserial`, `user_id uuid null`, `action text` (for example `recording.play`, `contacts.import`, `contact.erase`, `campaign.launch`), `object_type text`, `object_id text`, `ip text null`, `meta jsonb`, `created_at`.

### dnd_numbers
`phone_hash char(64) pk`, `added_at`. Imported by admin. Contacts matching this table are skipped at import.

---

## 5. Template script format

A template has a fixed set of **segments**. Every segment is a string with `{placeholder}` variables. The same keys exist in every translation.

| segment_key | purpose |
|---|---|
| `greeting` | Spoken first. Identifies the caller and the purpose. Must not contain personal data. |
| `prompt` | The question and the key options ("Press 1 to confirm, 2 to decline, 3 to reschedule. You can also say your answer."). |
| `reprompt` | Spoken once when input is missing or unclear. |
| `ack_confirm`, `ack_decline`, `ack_reschedule`, `ack_call_later` | Spoken after a captured intent. |
| `ack_stop` | Spoken after a stop-calling request. |
| `ack_unclear` | Spoken when we give up. |
| `voicemail` | Short message left on an answering machine (max 20 seconds). No personal or financial details. |
| `goodbye` | Final line. |

Example (`seminar` preset, English):

```json
{
  "greeting": "Hello. This is a call from {org_name} about {event_name}.",
  "prompt": "You are invited to {event_name} on {date} at {venue}. Press 1 to confirm, 2 to decline, or 3 to reschedule. You can also say your answer after the beep.",
  "reprompt": "Sorry, I did not catch that. Please press 1 to confirm, 2 to decline, or 3 to reschedule.",
  "ack_confirm": "Thank you. Your attendance is confirmed.",
  "ack_decline": "Thank you. We have noted that you cannot attend.",
  "ack_reschedule": "Thank you. We will contact you about another time.",
  "ack_call_later": "Thank you. We will call you again later.",
  "ack_stop": "Understood. We will not call you again.",
  "ack_unclear": "Sorry, we could not record your response. We may try again later.",
  "voicemail": "Hello, this is {org_name} inviting you to {event_name} on {date}. Please call us back to confirm.",
  "goodbye": "Thank you. Goodbye."
}
```

Rendering rules (Member 1 implements in `campaigns/prepare.py`):

1. Variables come from `campaign.event_details`. For a language `L`, any key in `campaign.variable_overrides[L]` replaces the base value.
2. `org_name` is a built-in variable read from env `ORG_NAME`.
3. Use a Jinja2 `SandboxedEnvironment` with `StrictUndefined` and single-brace delimiters implemented by converting `{key}` to `{{ key }}` first. Missing variable means the prepare step fails with error code `missing_variable`.
4. Translation happens on the template with placeholders protected. Substitution happens after translation. Variable values are inserted verbatim.
5. **No per-contact personalisation in v1.** No contact name is ever spoken. This keeps audio reusable across all contacts and keeps personal data out of the TTS service.

Presets to seed (Member 1): `seminar`, `clinic` (appointment reminder: confirm, reschedule), `school` (parent notice: acknowledge, call later), `payment` (reminder: will pay, need more time, `voicemail_policy = skip_and_retry`, `speech_enabled = false`, DTMF only).

---

## 6. REST API (owner: Member 1)

All routes require auth unless marked public. `{id}` values are UUIDs.

### Auth
| Method and path | Body | Response |
|---|---|---|
| POST `/api/auth/login` (public) | `{email, password}` | `{access_token, token_type:"bearer", user:{id,email,role}}` |
| GET `/api/auth/me` | | `{id,email,role}` |

### Templates
| Method and path | Notes |
|---|---|
| GET `/api/templates` | list, includes presets |
| POST `/api/templates` | create; body mirrors the `templates` table fields |
| GET `/api/templates/{id}` | |
| PUT `/api/templates/{id}` | allowed only while no running campaign uses it |
| GET `/api/templates/{id}/translations` | list with `status` per language |
| PUT `/api/templates/{id}/translations/{lang}` | body `{segments:{...}}`, sets `source=manual`, `status=draft` |
| POST `/api/templates/{id}/translations/{lang}/approve` | sets `status=approved`, records approver |
| POST `/api/templates/{id}/translations/{lang}/regenerate` | calls the AI service again |

### Campaigns
| Method and path | Body / notes | Response |
|---|---|---|
| POST `/api/campaigns` | `{name, template_id, event_details, variable_overrides?, languages[], caller_id?, calling_window_start?, calling_window_end?, max_attempts?, max_concurrent_calls?}` | campaign object |
| GET `/api/campaigns` | paginated | |
| GET `/api/campaigns/{id}` | | campaign + `readiness` (see below) |
| POST `/api/campaigns/{id}/contacts/import` | multipart `file` (CSV) | `{imported, skipped, errors:[{row, reason}]}` |
| POST `/api/campaigns/{id}/prepare` | starts translation (missing languages) and audio rendering | 202 `{status:"preparing"}` |
| POST `/api/campaigns/{id}/launch` | requires status `ready` | `{status:"running"}` |
| POST `/api/campaigns/{id}/pause` / `resume` / `cancel` | | `{status}` |
| GET `/api/campaigns/{id}/summary` | | see below |
| GET `/api/campaigns/{id}/breakdown?by=language\|segment` | | see below |
| GET `/api/campaigns/{id}/contacts?outcome=&language=&segment=&page=&page_size=` | masked phone (`+91XXXXXX3210`) | paginated rows |
| POST `/api/campaigns/{id}/retry` | `{outcomes?:[...], languages?:[...], segments?:[...]}`. Default `outcomes = NON_RESPONDER_SET`. | `{enqueued: n}` |
| GET `/api/campaigns/{id}/calls/{call_id}` | call detail with events and intents | |
| GET `/api/calls/{call_id}/recording` | streams audio, writes `audit_log` `recording.play` | audio |
| DELETE `/api/contacts/{id}` | right to erasure: deletes contact, deletes recordings, nulls the contact link in `campaign_contacts` | 204 |
| GET `/api/overview` | totals across campaigns for the home page | |
| POST `/api/admin/test-contacts` | admin only; body `{campaign_id, phone, language, segment?}`; creates a consenting contact and enqueues it, for sandbox tests with verified numbers. Audit logged. | contact id |

Public (no auth): GET `/media/audio/{sha256}.wav`, GET `/healthz`.

**Readiness object** (in GET campaign):
```json
{"has_contacts": true, "languages": {"hi": {"translation":"approved","audio":"ready"}, "ml": {"translation":"draft","audio":"missing"}}, "can_launch": false, "blockers": ["translation_not_approved:ml"]}
```

**Summary response**
```json
{
  "campaign_id": "uuid", "status": "running",
  "total_contacts": 200, "attempted": 140, "pending": 60, "exhausted": 12,
  "outcomes": {"confirmed": 70, "declined": 20, "reschedule": 5, "call_later": 3, "unclear": 6,
               "no_answer": 18, "busy": 4, "voicemail": 9, "failed": 1, "no_input": 4, "opted_out": 0, "pending": 60},
  "answer_rate": 0.71, "response_rate": 0.63,
  "updated_at": "2026-10-10T08:15:00Z"
}
```
`answer_rate = answered calls / attempted contacts`. `response_rate = contacts with an intent captured / answered contacts`. Outcome counts use `final_outcome` if set, otherwise `last_outcome`, otherwise `pending`. Every key is always present, zero-filled.

**Breakdown response**
```json
{"by": "language", "rows": [{"key": "hi", "total": 80, "outcomes": {"confirmed": 30, "...": 0}}]}
```

**CSV import format** (header required): `phone,name,language,segment,consent,dnd`. `consent` accepts `yes|true|1`. A row is skipped with a reason when: invalid phone (`invalid_phone`), unsupported language (`unsupported_language`), `consent` not true (`no_consent`), `dnd` true or hash in `dnd_numbers` (`dnd`), duplicate within the campaign (`duplicate`). Existing contacts (same `phone_hash`) are reused and their language and segment updated.

---

## 7. AI service API (owner: Member 3; stateless; internal network only, port 8200)

All endpoints are internal. The API service never exposes them publicly. Base URL for callers: `http://ai:8200`. Auth: header `X-Internal-Token` equal to env `AI_INTERNAL_TOKEN`.

### POST `/v1/stt`
Multipart: `audio` (wav, 8 kHz or 16 kHz, mono), `language` (hint, optional).
Response:
```json
{"text": "haan main aaunga", "language": "hi", "confidence": 0.82, "duration_ms": 2300, "latency_ms": 1800, "model": "faster-whisper-small"}
```

### POST `/v1/intent`
```json
{"text": "haan main aaunga", "language": "hi", "allowed_intents": ["confirm","decline","reschedule","call_later","stop_calling","unclear"]}
```
Response:
```json
{"intent": "confirm", "confidence": 0.93, "source": "rules", "latency_ms": 3}
```
`source` is `rules | model | llm`.

### POST `/v1/speech-intent`
Same multipart input as `/v1/stt` plus `allowed_intents` (JSON string). Runs VAD, STT and intent in one call to save a network round trip. Response is the union:
```json
{"text": "...", "language": "hi", "intent": "confirm", "confidence": 0.9, "source": "model", "stt_model": "faster-whisper-small", "latency_ms": 2100}
```
If the audio contains no speech: `{"text": "", "intent": "unclear", "confidence": 0.0, "source": "rules", "no_speech": true}`.

### POST `/v1/translate`
```json
{"segments": {"greeting": "Hello. This is a call from {org_name}.", "prompt": "..."},
 "source_language": "en", "target_language": "hi"}
```
Response `{"segments": {"greeting": "...", "prompt": "..."}, "model": "indictrans2-dist-200m"}`.
Must keep every `{placeholder}` intact. If a placeholder is lost the service retries once with the LLM fallback and, if still lost, returns HTTP 422 `placeholder_lost`.

### POST `/v1/tts`
```json
{"text": "नमस्ते...", "language": "hi", "voice": null}
```
Response: body is `audio/wav` (8 kHz, mono, 16-bit PCM). Headers: `X-Duration-Ms`, `X-Tts-Model`. The service stores nothing.

### GET `/healthz`
`{"status":"ok","models":{"stt":"loaded","intent":"loaded","translate":"loaded","tts":"loaded"}}`

Latency targets on the VPS (CPU): `/v1/intent` under 50 ms for rules, under 150 ms for the model; `/v1/speech-intent` under 4 s for a 5 s utterance; `/v1/tts` under 3 s per sentence with edge-tts.

---

## 8. Telephony contracts (owner: Member 2)

### 8.1 Provider interface

File `backend/app/telephony/providers/base.py`.

```python
@dataclass
class PlaceCallRequest:
    call_id: UUID
    to_number: str            # E.164, decrypted only inside this call
    caller_id: str            # ExoPhone
    status_callback_url: str
    flow_url: str             # URL the provider fetches when the callee answers
    custom_field: str         # str(call_id), echoed back by the provider
    time_limit_sec: int = 120

@dataclass
class PlaceCallResult:
    provider_call_sid: str
    accepted: bool
    raw_status: str

# Neutral call steps
@dataclass
class Play:    audio_url: str
@dataclass
class Gather:  prompt_audio_url: str | None; max_digits: int = 1; timeout_sec: int = 6; finish_on_key: str | None = None
@dataclass
class Record:  max_seconds: int = 6; silence_timeout_sec: int = 2; play_beep: bool = True
@dataclass
class Hangup:  pass
CallStep = Play | Gather | Record | Hangup

@dataclass
class ProviderEvent:
    type: Literal["initiated","ringing","answered","amd_result","dtmf","recording_ready","completed","failed"]
    provider_call_sid: str
    call_id: UUID | None      # from custom_field when present
    data: dict                # normalised: {"digits":"1"}, {"amd":"machine"}, {"recording_url":"..."}, {"status":"busy","duration":12}
    idempotency_key: str

class CallProvider(Protocol):
    name: str
    async def place_call(self, req: PlaceCallRequest) -> PlaceCallResult: ...
    async def hangup(self, provider_call_sid: str) -> None: ...
    def parse_webhook(self, kind: str, headers: Mapping, query: Mapping, body: Mapping) -> ProviderEvent: ...
    def render_steps(self, steps: list[CallStep]) -> Response: ...   # turns neutral steps into whatever the provider expects
    async def fetch_recording(self, url: str, dest: Path) -> Path: ...
```

Implementations: `MockProvider` (works with no network, built first) and `ExotelProvider`. Selected by env `CALL_PROVIDER=mock|exotel`.

### 8.2 Webhook endpoints (the path secret is `WEBHOOK_SECRET`)

| Route | Purpose |
|---|---|
| `GET|POST /webhooks/{secret}/flow` | Provider asks what to do now. Query includes `call_id`. Returns rendered steps. |
| `GET|POST /webhooks/{secret}/status` | Call status callback (ringing, answered, completed, busy, no-answer, failed). |
| `GET|POST /webhooks/{secret}/input` | Keypad digits and AMD result, when delivered separately from the flow request. |
| `GET|POST /webhooks/{secret}/recording` | Recording-ready callback. |
| `WS /ws/{secret}/voicebot` | Stretch goal only. Streaming audio if Exotel Voicebot is enabled. |

Every handler: validate the secret (constant-time compare), parse with `provider.parse_webhook`, insert into `call_events` using `idempotency_key` (duplicate means return 200 and stop), then run the flow engine. Always answer fast (under 1 s) except `/flow` which may take up to 4 s when it waits on speech classification.

**VERIFY AT KICKOFF** (Member 2 owns the answers, writes them into section 8.3):
1. Does `connect.json` accept a `Url` we host that returns call instructions (dynamic mode), or must it point to a flow built in the Exotel dashboard (static mode)?
2. Which parameter echoes our `call_id` back (`CustomField` is the expected name)?
3. Is answering machine detection available, and how is the result delivered?
4. Can we get the caller's spoken reply during the call (Record applet or Voicebot streaming), or only after the call?
5. Audio format required for Play (wav or mp3, sampling rate).
6. Sandbox limits: allowed destination numbers, concurrent calls, calling hours.

### 8.3 Exotel decisions (Member 2 fills in at kickoff; defaults used until then)

```
integration_mode:      dynamic   # fallback: static
speech_mode:           sync      # fallback: async (classify after the call; no in-call re-prompt)
amd_source:            exotel    # fallback: heuristic
audio_format:          wav 8kHz mono pcm16   # fallback: mp3
```

---

## 9. Call flow, state machine, retries (owner: Member 2)

### 9.1 Contact and call lifecycle

```
campaign_contact: pending ──place_call──> in_call ──call ends──> done | waiting_retry | exhausted
                  waiting_retry ──next_attempt_at reached──> in_call
call.status:      initiated → ringing → in_progress → completed
                  initiated|ringing → busy | no_answer | failed | canceled
```

### 9.2 Flow engine (pure function, fully unit-testable)

`flow.next(call_ctx, event) -> FlowDecision(steps: list[CallStep], intent: IntentResult | None, outcome: str | None, finalize: bool)`

`call.flow_state` JSON: `{"reprompts": 0, "speech_attempts": 0, "no_input_count": 0, "branch": "human|voicemail"}`.

| Event | Condition | Action |
|---|---|---|
| answered | `amd == machine` | branch `voicemail` (9.3) |
| answered | otherwise | steps `[Play(greeting), Gather(prompt, 1 digit, 6 s)]`, plus `Record` after the Gather if `speech_enabled` |
| dtmf digit | digit in `dtmf_map` | intent from map, confidence 1.0, source `dtmf`; play ack; hangup; outcome from intent |
| dtmf digit | digit not in map | treat as unclear input, go to reprompt rule |
| recording_ready | speech_enabled | call `/v1/speech-intent`; if `confidence >= threshold` and label is not `unclear` then play ack and hangup; else reprompt rule |
| no input (timeout) | `no_input_count == 0` | `no_input_count += 1`, play `reprompt`, Gather again |
| no input (timeout) | `no_input_count >= 1` | outcome `no_input`, play `goodbye`, hangup |
| reprompt rule | `reprompts == 0` | `reprompts += 1`, play `reprompt`, Gather again (DTMF emphasis) |
| reprompt rule | `reprompts >= 1` | outcome `unclear`, play `ack_unclear`, hangup |
| intent `stop_calling` or digit mapped to it | | set `contacts.opted_out = true`, outcome `opted_out`, play `ack_stop`, hangup |
| completed before any intent | call was answered | outcome `no_input`, `hangup_cause = caller_hangup` |
| completed | no answer | outcome from status: `no_answer`, `busy`, `failed` |

### 9.3 Voicemail branch

- `voicemail_policy = leave_message`: `[Play(voicemail), Hangup]`, outcome `voicemail`.
- `voicemail_policy = skip_and_retry`: `[Hangup]`, outcome `voicemail`.
- Either way the contact is retryable (`voicemail` is in `RETRYABLE_OUTCOMES`) and the call does not count as a human response.

### 9.4 Retry policy (default stored in `campaigns.retry_policy`)

```json
{"no_answer": 60, "busy": 30, "voicemail": 240, "failed": 15, "no_input": 120, "unclear": 1440, "call_later": 120}
```
Values are minutes until `next_attempt_at`. If `attempts >= coalesce(max_attempts_override, campaign.max_attempts)` the contact becomes `exhausted` and `final_outcome = last_outcome`. If the computed time is outside the calling window it is moved to the next window start. Terminal outcomes set `state = done` and `final_outcome`.

### 9.5 Scheduler rules

`dispatch_due_calls` runs every 10 seconds (Celery beat). For each running campaign:
1. Skip if the current time in `campaign.timezone` is outside `[calling_window_start, calling_window_end)`.
2. Compute free slots: `max_concurrent_calls` minus active calls (Redis counter, section 10), also capped by `EXOTEL_MAX_CONCURRENT`.
3. Select due rows: `state IN ('pending','waiting_retry') AND next_attempt_at <= now()` ordered by `next_attempt_at`, with `FOR UPDATE SKIP LOCKED`, limited to the free slots.
4. Skip and mark `skipped` any contact that is `opted_out`, `dnd`, or without `consent` (defence in depth; import already filters).
5. Mark rows `in_call`, enqueue `telephony.place_call`.

`sweep_stuck_calls` (every minute): any call in `initiated|ringing|in_progress` for more than 15 minutes becomes `failed` with `hangup_cause = timeout`, the slot is released and the retry rule applies.

### 9.6 Mock provider scenarios

The mock decides behaviour from the **last two digits** of the phone number, so tests are deterministic:

| Suffix | Behaviour |
|---|---|
| 01 | answered by human, presses 1 |
| 02 | answered, presses 2 |
| 03 | no answer |
| 04 | busy |
| 05 | voicemail (AMD `machine`) |
| 06 | answered, hangs up during the prompt |
| 07 | answered, speaks "yes" (uses `fixtures/audio/yes_{lang}.wav`) |
| 08 | answered, mumbles (unclear) then presses 1 |
| 09 | answered, presses 9 (stop calling) |
| 10 | answered, silence twice (`no_input`) |
| other | random mix |

The mock runs inside the worker and calls the real webhook handlers over HTTP, so the whole pipeline is exercised.

---

## 10. Celery tasks and Redis keys

Broker and result backend: Redis DB 0 and 1 of the project's own Redis.

| Task name | Owner | Trigger |
|---|---|---|
| `campaigns.prepare_campaign(campaign_id)` | M1 | POST prepare |
| `maintenance.purge_expired_recordings()` | M1 | daily 03:00 IST |
| `maintenance.purge_expired_events()` | M1 | daily |
| `telephony.dispatch_due_calls()` | M2 | beat every 10 s |
| `telephony.place_call(campaign_contact_id)` | M2 | dispatcher |
| `telephony.fetch_recording(call_id)` | M2 | on recording webhook |
| `telephony.sweep_stuck_calls()` | M2 | beat every 60 s |

Redis keys (prefix `pr002:`): `pr002:camp:{campaign_id}:active_calls` (integer counter with a safety TTL of 900 s refreshed on change), `pr002:rate:exotel` (token bucket for call placement per second), `pr002:lock:prepare:{campaign_id}` (prepare mutex, 600 s), `pr002:prepare_error:{campaign_id}` (last prepare failure message, 1 hour TTL).

---

### Shared Python helpers (cross-member function contracts)

| Function | Owner | Used by |
|---|---|---|
| `backend.app.analytics.queries.maybe_complete(campaign_id)` | M1 | M2 calls it after every call finalisation |
| `backend.app.security.crypto.reveal_phone(contact) -> str` | M1 | M2, only inside `place_call` |
| `backend.app.security.crypto.encrypt_bytes / decrypt_bytes` | M1 | M2 stores recordings with it |
| `backend.app.telephony.flow.engine.next(call_ctx, event) -> FlowDecision` | M2 | webhook handlers |
| `AIClient.speech_intent / intent / translate / tts` | M1 (client), M3 (server) | M1, M2 |

## 11. Environment variables

Defined in `.env.example` (Member 4 maintains). Never commit real values.

```
# core
APP_ENV=dev|prod
PUBLIC_BASE_URL=https://api.example.com
WEB_ORIGIN=https://app.example.com       # CORS allow-list
DATABASE_URL=postgresql+psycopg://pr002:***@postgres:5432/pr002
REDIS_URL=redis://:***@redis:6379/0
JWT_SECRET=...
ORG_NAME=Demo Institute
ADMIN_EMAIL=...   ADMIN_PASSWORD=...     # seeded on first start
# security
DATA_ENC_KEY=<base64 32 bytes>            # AES-256-GCM for phones, names, recordings
PHONE_HMAC_KEY=<base64 32 bytes>
WEBHOOK_SECRET=<random 32+ chars>
RECORDING_RETENTION_DAYS=30
EVENT_RETENTION_DAYS=90
# storage
MEDIA_DIR=/data/media
RECORDINGS_DIR=/data/recordings
# telephony
CALL_PROVIDER=mock|exotel
EXOTEL_SID=  EXOTEL_API_KEY=  EXOTEL_API_TOKEN=  EXOTEL_SUBDOMAIN=  EXOTEL_CALLER_ID=
EXOTEL_MAX_CONCURRENT=3
# ai service
AI_BASE_URL=http://ai:8200
AI_INTERNAL_TOKEN=...
STT_MODEL=faster-whisper-small
LLM_FALLBACK=gemini|groq|none
GEMINI_API_KEY=  GROQ_API_KEY=
TTS_ENGINE=edge|parler
```

---

## 12. Docker Compose services and ports (owner: Member 4)

| Service | Image source | Host port | Notes |
|---|---|---|---|
| `postgres` | postgres:16 | none | volume `pgdata`, internal network only |
| `redis` | redis:7 | none | password required, volume `redisdata`, internal only |
| `api` | `services/api` | `127.0.0.1:8100` | FastAPI, uvicorn, 2 workers |
| `worker` | `services/api` | none | `celery -A app.celery_app worker -Q default -c 4` |
| `beat` | `services/api` | none | `celery -A app.celery_app beat` |
| `ai` | `services/ai` | none (8200 internal) | volume `models` for model weights |
| `web` | `apps/web` | `127.0.0.1:8101` | Next.js production build |

Volumes: `pgdata`, `redisdata`, `media` (mounted at `/data/media` in `api` and `worker`), `recordings` (`/data/recordings`), `models` (`/root/.cache/huggingface` in `ai`). Compose project name `pr002`, network `pr002_net`. Public hostnames (through the existing host Caddy): `api.<domain>` to 8100, `app.<domain>` to 8101. The `/media/audio/*` route is served by `api`.

---

## 13. Fixtures (shared, in `fixtures/`)

- `contacts_sample.csv`: 20 rows, mixed languages `en,hi,ml,ta`, segments `students,faculty,alumni`, phone numbers using the mock suffix scheme (`+9199999000NN`).
- `template_seminar.json`: the seminar example in section 5.
- `audio/yes_hi.wav`, `no_hi.wav`, `yes_ml.wav`, `no_ml.wav`, `yes_ta.wav`, `no_ta.wav`, `yes_en.wav`, `no_en.wav`, `noise.wav`: recorded by the team on a phone call or downsampled to 8 kHz. Member 3 owns recording and naming.
