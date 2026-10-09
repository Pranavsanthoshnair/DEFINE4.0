# Member 1 — Backend Core, Data and Compliance

**You own:** the database, the REST API, the campaign preparation pipeline, CSV import, analytics and retry API, encryption, audit log, retention, and the privacy document.

**Read first:** `PRD.md` and `CONTRACTS.md` (sections 1 to 7, 10, 11 are yours or directly affect you). Do not change contracts silently. If you need a change, open a `contract-change` PR.

**If you are using an AI coding agent:** give it this file plus `CONTRACTS.md`. The agent must not invent table columns, endpoint paths, enum values, or env var names. Everything it needs is specified. If something is missing, it must stop and ask rather than choose.

---

## 1. What you deliver

1. Alembic migrations and SQLAlchemy models exactly as in `CONTRACTS.md` section 4.
2. FastAPI app with every route in `CONTRACTS.md` section 6.
3. Crypto module (AES-GCM, HMAC), auth module, audit logging.
4. CSV import with per-row validation.
5. `prepare_campaign` Celery task: translation, rendering, TTS, audio assets.
6. Analytics: summary, breakdown, contacts list, retry.
7. Four presets seeded.
8. Retention and erasure.
9. `docs/PRIVACY.md`.
10. A typed client for the AI service (`services/api/app/ai_client/`).
11. Tests with at least 80 percent coverage of your modules.

## 2. Directory ownership

```
services/api/app/
  main.py, config.py, celery_app.py
  db/models.py, db/session.py, db/migrations/
  security/crypto.py, security/auth.py, security/audit.py
  campaigns/{router.py, service.py, csv_import.py, prepare.py, schemas.py}
  templates/{router.py, service.py, schemas.py, presets/*.json}
  analytics/{router.py, queries.py}
  ai_client/{client.py, schemas.py}
services/api/tests/
docs/PRIVACY.md
```
`app/telephony/` belongs to Member 2. Mount their routers in `main.py` with `app.include_router(telephony_router)` once they provide it. Until then, leave a clearly marked placeholder.

## 3. Tech and libraries

Python 3.12, FastAPI, uvicorn, Pydantic v2, SQLAlchemy 2.0 (typed, `Mapped[...]`), Alembic, `psycopg` v3, `argon2-cffi`, `PyJWT`, `cryptography` (AESGCM), Jinja2, httpx, Celery with Redis, structlog, pytest, pytest-asyncio, `ruff`. Pin versions in `pyproject.toml` with a lockfile (use `uv` or `pip-tools`).

## 4. Phase plan

### Phase 0 — Setup (with everyone)
- Create `services/api` scaffold, `pyproject.toml`, Dockerfile (one image used by `api`, `worker`, `beat`).
- `GET /healthz` returns `{"status":"ok"}`.
- `config.py`: pydantic-settings class reading all env vars in `CONTRACTS.md` section 11. Fail fast on missing secrets in `prod`.
- Structlog JSON logging with a processor that redacts keys named `phone`, `to_number`, `name`, `transcript`.
**Done when:** `docker compose up api` serves `/healthz` and `ruff` and `pytest` run in CI.

### Phase 1 — Foundations (largest part of your work)

**1.1 Models and migrations.**
Implement every table in `CONTRACTS.md` section 4 with the exact names. Add indexes: `campaign_contacts(campaign_id, state, next_attempt_at)`, `calls(campaign_contact_id)`, `call_events(provider_call_sid)`, `intents(call_id)`, `contacts(phone_hash)` unique. Use `CheckConstraint` for the enum-like text columns. Provide a seed command `python -m app.db.seed` that creates the admin user from env and inserts the four presets (idempotent).
Done when: `alembic upgrade head` on an empty database works, `alembic downgrade base` works.

**1.2 Crypto (`security/crypto.py`).**
```python
def encrypt(plaintext: str) -> bytes        # AES-256-GCM, random 12-byte nonce, returns nonce + ciphertext_with_tag
def decrypt(blob: bytes) -> str
def phone_hash(e164: str) -> str            # HMAC-SHA256 hex using PHONE_HMAC_KEY
def normalise_phone(raw: str) -> str | None # to E.164, 10 digits means +91, returns None if invalid
def mask_phone(e164: str) -> str            # +91XXXXXX3210
def encrypt_bytes(data: bytes) -> bytes     # for recordings, same scheme
def decrypt_bytes(blob: bytes) -> bytes
```
Keys come from base64 env vars. Unit tests: round trip, tamper detection raises, hash is deterministic, normalise table (`9876543210`, `+91 98765 43210`, `09876543210`, `abc`, `+1415...`).

**1.3 Auth (`security/auth.py`).**
`POST /api/auth/login`, `GET /api/auth/me`, dependency `current_user`, `require_role("admin")`. Argon2 password hashing. JWT HS256, 12 hour expiry. Login failures return the same message for unknown email and wrong password.

**1.4 Templates and presets.**
Routes in `CONTRACTS.md` section 6. Presets stored as JSON in `templates/presets/` and loaded by the seed command. Each preset provides the full English `script` for every segment key in section 5 of the contracts, `variables`, `dtmf_map`, `speech_enabled`, `voicemail_policy`:

| Preset | dtmf_map | speech_enabled | voicemail_policy |
|---|---|---|---|
| seminar | 1 confirm, 2 decline, 3 reschedule, 9 stop_calling | true | leave_message |
| clinic | 1 confirm, 2 reschedule, 9 stop_calling | true | leave_message |
| school | 1 confirm (acknowledge), 2 call_later, 9 stop_calling | true | leave_message |
| payment | 1 confirm (will pay), 2 call_later, 9 stop_calling | false | skip_and_retry |

Write preset text in simple spoken English: short sentences, no abbreviations, numbers written as words where a TTS could misread them. Keep the `prompt` under 25 seconds when spoken.

**1.5 Campaign CRUD.**
Validation: all `languages` must be among the supported set; `template_id` must exist; every required template variable must be present in `event_details` (error `missing_variable`); `calling_window_end > calling_window_start`. Status transitions enforced in one function `transition(campaign, new_status)` that raises `409 invalid_transition`. Allowed: `draft→preparing→needs_review|ready`, `needs_review→preparing`, `ready→running`, `running↔paused`, `running→completed`, `draft|ready|running|paused→cancelled`. Completion: a Celery-independent check run after each call finalisation (Member 2 calls `analytics.service.maybe_complete(campaign_id)`) marks `completed` when no contact is in `pending|in_call|waiting_retry`.

**1.6 CSV import (`csv_import.py`).**
Stream the file (max 5 MB, max 10 000 rows). Use `csv.DictReader`. Required header: `phone,name,language,segment,consent,dnd`. Per row, in order: normalise phone (`invalid_phone`), language supported (`unsupported_language`), consent true (`no_consent`), dnd flag or hash in `dnd_numbers` (`dnd`), duplicate within this campaign (`duplicate`). Upsert `contacts` by `phone_hash` (update language, segment, name, consent fields), then insert `campaign_contacts` with `state='pending'`, `next_attempt_at=now()`. Contacts with `opted_out=true` are skipped with reason `opted_out`. Respond `{imported, skipped, errors:[{row, reason}]}`; `row` is the 1-based data row number. Use bulk inserts in batches of 500 inside one transaction per batch. Write an `audit_log` entry `contacts.import` with counts only.
Done when: the fixtures CSV imports 20 rows, and a crafted bad CSV yields the right error reasons.

**1.7 AI client (`ai_client/client.py`).**
Async httpx client with typed methods `translate`, `tts`, `intent`, `stt`, `speech_intent` matching `CONTRACTS.md` section 7. Add header `X-Internal-Token`. Timeouts: translate 60 s, tts 30 s, others 10 s. Retry once on 5xx or timeout. Provide a `FakeAIClient` used in tests and when env `AI_BASE_URL` is empty.

**1.8 Analytics (`analytics/queries.py`).**
Implement `summary`, `breakdown(by)`, `contacts_page`, `overview` exactly as in the contracts. Outcome per contact is `coalesce(final_outcome, last_outcome, 'pending')`. Use a single grouped SQL query per call (no per-row loops). Zero-fill every outcome key. Provide an index plan note in code comments if you add any.
Done when: with seeded rows the numbers match hand-computed expectations in tests.

**Phase 1 exit check (with M2):** run a mock campaign end to end. Create campaign, import fixtures, prepare (using `FakeAIClient`), launch, wait, then `GET /summary` shows each mock scenario in the right bucket.

### Phase 2 — Exotel support
- Add a `caller_id` default from `EXOTEL_CALLER_ID`.
- Add admin-only `POST /api/admin/test-contacts` that creates a contact from a raw number for sandbox tests (audit logged). This avoids hand-made CSVs for the verified test numbers.
- Make sure public media route `/media/audio/{sha256}.wav` is served with `Content-Type: audio/wav`, `Cache-Control: public, max-age=3600`, and rejects any name that is not 64 hex characters plus `.wav` (path traversal protection). Support HTTP range requests (use Starlette `FileResponse`).

### Phase 3 — Reliability, retry API
- `POST /api/campaigns/{id}/retry`: in one transaction, for matching `campaign_contacts` (by `coalesce(final_outcome,last_outcome)` in the requested outcomes, optional language and segment filters; never `opted_out` contacts; campaign must be `running` or `paused` or `completed`), set `state='waiting_retry'`, `next_attempt_at=now()`, `max_attempts_override = attempts + 1`, `final_outcome = NULL`. If the campaign was `completed`, set it back to `running`. Return `{enqueued: n}`. Audit log `campaign.retry`.
- `GET /api/campaigns/{id}/calls/{call_id}`: call row, ordered `call_events` (payload already masked), `intents`, and `recording` availability flag.
- `GET /api/calls/{call_id}/recording`: decrypt the file on the fly (`decrypt_bytes`), stream as `audio/wav` (or the stored type), write `audit_log` `recording.play`. 404 if missing, 403 for non-admin and non-owner organisers (organiser can play only recordings of campaigns they created).

### Phase 4 — Preparation pipeline (`campaigns/prepare.py`)
Task `campaigns.prepare_campaign(campaign_id)`:
1. Acquire Redis lock `pr002:lock:prepare:{id}`; set status `preparing`.
2. For each language in `campaign.languages` other than the template source language: if no `template_translations` row, call `ai.translate(script, source, target)`, store with `status='draft'`, `source='ai'`. If the AI call fails after retries, do not add a database column for the error. Store the failure message in the Redis key `pr002:prepare_error:{id}` (1 hour TTL) and set the campaign status back to `draft`. Surface it in the readiness object as blocker `translation_failed:{lang}`.
3. If any required language translation is still `draft`, set status `needs_review` and stop. For the source language, treat the template script as approved.
4. Otherwise render each segment per language (section 5 rules in the contracts) and for each `(language, segment_key)`: compute `sha256(text + language + TTS_ENGINE)`. If an `audio_assets` row with the same sha already exists for this campaign, skip. Otherwise call `ai.tts`, write WAV to `MEDIA_DIR/audio/{sha}.wav` atomically (write temp file then rename), insert `audio_assets`.
5. Set status `ready`.
Translation approval endpoint must re-trigger `prepare_campaign` for every campaign in `needs_review` that uses that template.
Done when: three languages prepared from a seminar template, all `audio_assets` exist on disk, readiness shows `can_launch: true`.

### Phase 5 — Compliance and hardening
- `maintenance.purge_expired_recordings`: delete files older than `RECORDING_RETENTION_DAYS` by `calls.ended_at`, set `recording_path = NULL`, audit log `recording.purge` with the count.
- `maintenance.purge_expired_events`: delete `call_events` older than `EVENT_RETENTION_DAYS`.
- `DELETE /api/contacts/{id}`: admin only. Delete recording files, null `recording_path`, delete `intents.raw_input` content for that contact's calls (set to `''`), delete the contact row (set `campaign_contacts.contact_id` handling per the schema: make that FK `ON DELETE SET NULL` in the migration and keep the row for statistics), audit log.
- Verify that no log line contains a phone number: add a test that runs an import and a call simulation and greps captured logs for the test numbers.
- Rate-limit `POST /api/auth/login` (5 attempts per minute per IP, in Redis).
- CORS: allow only the web origin from env `WEB_ORIGIN` (add this variable to `.env.example`).
- Write **`docs/PRIVACY.md`** (see section 6 below).

### Phase 6 — Demo support
- `python -m app.db.demo_seed`: creates a demo campaign with about 200 contacts and realistic outcome history (fake calls and intents marked as seeded) so the dashboard looks populated if the live demo fails. Never mix seeded rows into a real campaign: use a campaign named `DEMO (seeded)`.

## 5. Acceptance tests you must write

- Auth: login ok, wrong password, role guard.
- Crypto tests listed above.
- CSV: valid file, each error reason, duplicates, existing contact reuse, size limit.
- Campaign validation and status transition table (all allowed and a sample of forbidden).
- Prepare pipeline with `FakeAIClient`: translation draft leads to `needs_review`, approve leads to `ready`; placeholder substitution with and without overrides; missing variable error.
- Analytics numbers on a seeded dataset with every outcome.
- Retry endpoint: only requested outcomes, `max_attempts_override` set, opted-out excluded.
- Recording endpoint: authorisation and audit entry.
- Erasure: files gone, contact gone, stats preserved.

## 6. `docs/PRIVACY.md` contents (required sections)

1. Purpose and scope (what personal data we handle: phone numbers, names, language, segment, call recordings, transcripts and intents).
2. Lawful basis and consent: consent flag required at import, source recorded, opt-out on every call, DND handling, calling-hours policy. Mention that regulations (India's DPDP Act, telecom commercial communication rules) apply and that production use needs a legal review.
3. Data inventory table: data item, where stored, encrypted or not, retention.
4. **Processing locations table** (this is a graded item): for each of contact storage, call audio, speech to text, intent classification, translation, text to speech, telephony, state the system, location (VPS provider, city, country; Exotel region), and whether data leaves our server. Use the table in `PRD.md` section 7 as the starting point and replace placeholders with confirmed facts. Ask the VPS owner for provider and data-centre location.
5. Third-party processors list: Exotel, and optional Gemini or Groq (fallback only) and Microsoft (edge-tts, template text only). State what each receives.
6. Security measures: encryption at rest and in transit, key handling, access control, audit log, webhook secret, firewall, no secrets in git.
7. Retention and deletion: defaults, erasure endpoint, how to change retention.
8. Data subject rights and contact point.
9. Known limitations (honest section): free-tier or unofficial TTS, no real DND registry integration, single server, no formal certification.

## 7. Rules and pitfalls

- Never decrypt phone numbers except inside Member 2's `place_call` path. Add a `reveal_phone(contact)` helper in `crypto.py` that writes no logs, and only that path imports it. Grep for other uses in review.
- Never accept raw SQL strings built from user input. Use bound parameters.
- Never return `phone_enc`, `name_enc` or hashes in any API response.
- Do not add columns, enum values or endpoints without a `contract-change` PR.
- Time handling: always timezone-aware UTC objects; never `datetime.utcnow()`.
- Keep route handlers thin; put logic in `service.py` so Member 2 can reuse functions (for example `maybe_complete`).
- Idempotent seed and migrations. Re-running must be harmless.

## 8. Hand-offs

| To | What | When |
|---|---|---|
| M2 | Models and migrations merged, `maybe_complete` function, `reveal_phone` helper | end of Phase 1 start |
| M4 | OpenAPI JSON exported to `fixtures/openapi.json` on every merge; example responses for each analytics endpoint | Phase 1 early |
| M3 | Review of AI contract usage; confirm `FakeAIClient` matches real responses | Phase 1 |
| M4 | Provider, region facts for `PRIVACY.md` and the in-app privacy page text | Phase 5 |

## 9. Definition of done checklist

- [ ] Every route in contracts section 6 exists and has tests.
- [ ] OpenAPI exported and current.
- [ ] Migrations upgrade and downgrade cleanly.
- [ ] No phone numbers or transcripts in logs (tested).
- [ ] `PRIVACY.md` complete with confirmed processing locations.
- [ ] Demo seed works.
- [ ] Coverage at least 80 percent on owned modules.
