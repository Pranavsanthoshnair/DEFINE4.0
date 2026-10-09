# PR 002 — Multilingual Outbound Calling Campaign Platform
## Product Requirements Document (v1.0)

Related documents: `CONTRACTS.md` (shared technical contracts), `members/member-1..4` (per-member implementation docs).

---

## 1. Summary

Institutions run seminars and workshops and must phone many people for invitations, RSVPs, reminders and updates. Recipients speak different languages. Manual calling is slow, costly and inconsistent.

We are building a platform where an organiser supplies a **message template and event details** and gets a **live multilingual phone-calling campaign** with minimal effort. The platform places the calls through Exotel, captures each person's intent by keypad and/or speech, handles voicemail and other real-world call outcomes, and shows results on a dashboard with a one-click retry for non-responders. The platform is template-driven so the same engine serves seminars, clinic reminders, school-to-parent messages and payment reminders.

## 2. Goals and non-goals

### Goals
- G1. Launch a campaign in under 5 minutes from a template and a contact CSV.
- G2. Place calls in each contact's preferred language, several languages in one campaign. Demo set: English, Hindi, Malayalam, Tamil.
- G3. Capture intent reliably with keypad (always) and speech (when enabled), with a sensible fallback when unclear.
- G4. Handle no-answer, busy, voicemail, hang-ups and failures correctly, with retries.
- G5. Dashboard with outcomes by campaign, language and audience segment, and a retry action.
- G6. Treat contact lists and recordings as personal data, with a written statement of where processing happens.
- G7. Generic design: four use-case presets prove the platform is not seminar-specific.

### Non-goals (v1)
- Free-form conversational voice agent (documented as future work).
- Per-contact personalised audio (names are never spoken).
- Inbound calling, SMS, WhatsApp.
- Integration with the real national DND registry (we implement a local DND list and consent flag).
- Training ASR or TTS models from scratch.
- Multi-tenant organisations and billing.

## 3. Users

| User | Needs |
|---|---|
| **Organiser** | Create a campaign fast, trust the translations, see who is coming, retry people who did not respond. |
| **Admin** | Manage users, DND list, retention, access to recordings. |
| **Recipient** | A short, clear call in their own language, easy way to answer or opt out. |
| **Judge** | Evidence of reasoned design, working end to end demo, privacy thinking, generality. |

## 4. Functional requirements

Priority: **P0** must work in the demo, **P1** should work, **P2** stretch.

### 4.1 Campaign creation
| ID | Requirement | Priority |
|---|---|---|
| FR-1 | Pick a template (preset or custom) and enter event details (variables). | P0 |
| FR-2 | Upload contacts by CSV with phone, name, language, segment, consent, dnd. Validation errors are reported per row. | P0 |
| FR-3 | System translates the template into every campaign language automatically. An organiser reviews and approves each translation before launch. | P0 |
| FR-4 | System renders all call audio per language before launch (text to speech) and caches it. | P0 |
| FR-5 | Launch, pause, resume and cancel a campaign. | P0 |
| FR-6 | Calling window (default 09:00 to 21:00 IST), max attempts, max concurrent calls are configurable per campaign. | P0 |
| FR-7 | Four seeded presets: seminar, clinic, school, payment. | P0 |

### 4.2 Calling and intent capture
| ID | Requirement | Priority |
|---|---|---|
| FR-8 | Outbound calls through Exotel to verified test numbers. A mock provider supports development and automated tests. | P0 |
| FR-9 | Keypad capture: template `dtmf_map` maps digits to intents. | P0 |
| FR-10 | Speech capture: caller reply is transcribed and classified into `confirm`, `decline`, `reschedule`, `call_later`, `stop_calling`, `unclear`. | P1 |
| FR-11 | Fallback: unclear input leads to one re-prompt that emphasises keypad options, then outcome `unclear`. | P0 |
| FR-12 | Opt-out: saying or pressing stop sets `opted_out` immediately and the contact is never called again by any campaign. | P0 |
| FR-13 | Voicemail detection. Policy per template: leave a short message, or skip and retry. A voicemail never counts as a human response. | P0 |
| FR-14 | Real-world outcomes recorded: no answer, busy, failed, hang-up mid-call, no input. | P0 |
| FR-15 | Automatic retries by outcome with backoff, inside the calling window, up to max attempts. | P0 |

### 4.3 Dashboard
| ID | Requirement | Priority |
|---|---|---|
| FR-16 | Campaign summary: totals, outcome counts, answer rate, response rate. | P0 |
| FR-17 | Breakdown by language and by audience segment. | P0 |
| FR-18 | Contact table with filters (outcome, language, segment) and masked phone numbers. | P0 |
| FR-19 | "Retry non-responders" action, with optional filters by outcome, language, segment. | P0 |
| FR-20 | Call detail view: timeline of events, captured intent, recording playback (authorised and audited). | P1 |
| FR-21 | Home overview across campaigns. | P1 |

### 4.4 Data protection
| ID | Requirement | Priority |
|---|---|---|
| FR-22 | Phone numbers and names encrypted at rest (AES-256-GCM). Lookups by HMAC hash. | P0 |
| FR-23 | Recordings stored encrypted, accessible only to authenticated users, every access written to `audit_log`. | P0 |
| FR-24 | Retention: recordings deleted after `RECORDING_RETENTION_DAYS` (default 30). | P0 |
| FR-25 | Right to erasure: delete a contact and their recordings on request. | P1 |
| FR-26 | Written statement of where voice and language processing happens (`docs/PRIVACY.md`, also shown in the app). | P0 |
| FR-27 | Consent flag required to enqueue a contact. DND flag and DND list respected. | P0 |

### 4.5 Deliverables mapping (from the problem statement)
| Deliverable | Covered by |
|---|---|
| 1. Campaign creation flow | FR-1 to FR-7 |
| 2. Working outbound calls through Exotel | FR-8 |
| 3. Intent capture (speech, keypad or both) | FR-9 to FR-12 |
| 4. Voicemail detection and handling | FR-13 |
| 5. Dashboard by campaign, language, segment, plus retry | FR-16 to FR-19 |
| 6. Data-protection and processing-location statement | FR-22 to FR-27, `docs/PRIVACY.md` |
| 7. Written justification of calling approach | Section 6 of this PRD, finalised in `docs/CALLING_APPROACH.md` |

## 5. Non-functional requirements

| Area | Target |
|---|---|
| In-call latency | Keypad response under 1 s. Speech path under 4 s from end of speech to next prompt. If speech latency cannot meet this, switch to async mode (contract `speech_mode: async`). |
| Capacity | 5 simultaneous calls in the demo, sustained dispatch of at least 1 call per second. Sandbox caps may be lower. |
| Reliability | Webhooks are idempotent. A crashed worker never leaves a contact stuck: the sweeper recovers in 15 minutes at most. |
| Security | HTTPS only. Webhook path secret. Internal AI service not exposed publicly. No secrets in git. SSH key-only access. |
| Privacy in logs | No phone numbers, names or transcripts in logs. |
| Observability | Raw events stored per call. JSON logs. Health endpoints on every service. |
| Accuracy (intent) | Macro F1 of at least 0.90 on the synthetic test set per demo language, and at least 0.80 on a small hand-recorded set. |

## 6. Calling approach decision (written justification, draft)

We evaluated three approaches.

| Approach | Strength | Weakness |
|---|---|---|
| Pre-recorded or pre-rendered scripted messages with keypad (IVR) | Cheap, predictable, zero in-call latency, works on any phone, easy to audit | Rigid, free speech is not understood |
| Fully conversational voice agent | Handles free-form replies | Costlier, high latency over narrow-band phone audio, error and hallucination risk, hard to guarantee compliance wording |
| Hybrid | Combines both | More complex |

**Decision: hybrid, with a scripted backbone.**

1. Every call follows a scripted flow with pre-rendered audio and a keypad fallback. Audio is generated once per language per campaign, so the call never waits for text to speech.
2. Speech understanding is a layer on the same flow, limited to one short reply per prompt classified into a fixed intent set. It is not an open conversation. This gives the convenience of "just say yes" without the latency and risk of free-form dialogue.
3. Risk drives the mode per use case. Payment reminders are high stakes (wrong interpretation has a financial cost), so the `payment` preset is DTMF only and does not leave detailed voicemail. RSVP-style messages (seminar, clinic) enable speech because a wrong reading is low cost and the keypad is always available.
4. If speech confidence is below the threshold we ask once more, stressing the keypad, then record `unclear`. We never guess.
5. A conversational agent remains a documented extension point: the flow engine returns neutral call steps, so a streaming voicebot can be added without changing campaign logic.

## 7. Architecture

```
Organiser UI (Next.js)
        |
   REST API (FastAPI)  ---- PostgreSQL
        |                        ^
   Celery worker + beat ---------|
     |  prepare_campaign: translate -> render -> TTS (calls AI service)
     |  dispatch_due_calls -> place_call (CallProvider)
     v
  CallProvider ---- Exotel (or Mock)
        |                      |
        |<---- webhooks: flow, status, input, recording ----|
        v
  Flow engine (state machine) ---> AI service (STT, intent, translate, TTS)
        |
  Postgres events, intents, calls ---> Dashboard
```

### Technology stack

| Part | Choice |
|---|---|
| UI | Next.js (App Router), TypeScript, Tailwind, shadcn/ui, TanStack Query, TanStack Table, recharts, react-hook-form, zod, papaparse |
| API | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, argon2, PyJWT, Jinja2 (sandboxed), httpx, structlog |
| Queue and scheduler | Celery 5 with Redis, Celery beat |
| Database | PostgreSQL 16 (JSONB, `SKIP LOCKED` for dispatch) |
| AI service | FastAPI, faster-whisper, silero-vad, ONNX Runtime, transformers, IndicTrans2 (distilled), edge-tts, ffmpeg |
| Fine-tuned model | MuRIL (or IndicBERT v2) for intent, exported to ONNX int8 |
| Telephony | Exotel; `CallProvider` abstraction with `MockProvider` |
| Infra | Docker Compose on our VPS, existing host Caddy for HTTPS, `ufw`, nightly `pg_dump` |

### Processing locations (summary; final text in `docs/PRIVACY.md`)

| Data and processing | Where | Leaves our server? |
|---|---|---|
| Contact list, names, phone numbers | Our VPS Postgres, encrypted columns | No |
| Call audio from Exotel (recordings) | Exotel (telephony provider) during the call, then copied to our VPS, encrypted | Exotel is the carrier, so audio transits it by necessity |
| Speech to text | Self-hosted models on our VPS | No |
| Intent classification | Self-hosted rules and fine-tuned model on our VPS | No |
| Translation of templates | Self-hosted IndicTrans2 on our VPS. LLM API (Gemini or Groq) only as a fallback, template text only, no personal data | Only template text, only on fallback |
| Text to speech | edge-tts calls a Microsoft cloud service with template text only (no personal data). Optional self-hosted Parler-TTS replaces it | Template text only |

State the VPS provider, region and country in `docs/PRIVACY.md` once confirmed (Member 1 collects this from the VPS owner).

## 8. Locked product decisions

These are decided. Do not reopen without a `contract-change` PR.

1. Hybrid scripted-plus-speech approach (section 6).
2. No per-contact personalised audio. No names spoken.
3. Translation is reviewed by a human and approved per template and language before any campaign using that language can launch.
4. Audio is pre-rendered per campaign, language and segment key and served from our own `/media/audio/` route.
5. The AI service is stateless. It returns bytes and JSON and stores nothing.
6. One Postgres, one Redis, project-owned, internal network only. MinIO is **not** used (media and recordings live on Docker volumes).
7. Outcome vocabulary and retry rules are exactly those in `CONTRACTS.md` sections 3 and 9.
8. Default calling window 09:00 to 21:00 IST. Check current telecom regulation (TRAI rules) before the final submission and update the default if needed.
9. Keypad is always available. Speech is optional per template.
10. Phone numbers are never logged and never sent to any AI service.

## 9. Delivery plan

Phases are ordered by dependency, not by clock time. Suggested share of total hackathon time in brackets. Adjust once kickoff timing is known. Phases 0 and 1 can be done **before** Exotel access exists, because everything runs against the mock provider.

### Phase 0 — Setup and contract freeze (5%)
All members. Create the repo, branch rules, scaffolds, `.env.example`, Compose skeleton, CI lint. Read and agree on `CONTRACTS.md`.
**Exit:** `docker compose up` starts all services healthy. Every member can run the stack locally. Contracts tagged `v1.0`.

### Phase 1 — Foundations on mocks (25%)
- M1: schema, migrations, auth, template and campaign CRUD, CSV import, presets, encryption module.
- M2: `CallProvider`, `MockProvider`, flow engine with unit tests, scheduler and tasks, webhook handlers.
- M3: AI service skeleton with canned responses, test audio recording, intent dataset generation started, STT benchmark started.
- M4: dashboard pages on fake data (mock service worker), VPS user and Caddy snippet, Compose, CI.
**Exit:** an end-to-end mock campaign works: create campaign via API, import fixtures CSV, launch, mock calls run through the real webhooks, `GET /summary` returns correct counts, dashboard renders fake data.

### Phase 2 — Exotel integration and keypad flow (15%)
Starts at kickoff. M2 builds `ExotelProvider`, answers the VERIFY items, runs real test calls. M4 exposes public HTTPS webhooks and audio URLs. M1 supports contact data for test numbers. M3 supplies real pre-rendered audio for at least Hindi and English.
**Exit:** a real call to a test number plays the greeting and prompt, captures a keypad digit, and records the outcome in the database.

### Phase 3 — Reliability and real-world behaviour (15%)
M2: status webhooks, retries, voicemail, hang-up handling, calling windows, rate limit, sweeper. M1: analytics queries, retry API. M4: dashboard on live data and the retry button.
**Exit:** all scenarios in the test matrix (section 10) pass on the mock, and at least no-answer, answered-confirm and answered-decline pass on Exotel.

### Phase 4 — Multilingual and speech (20%)
M3: real translation, TTS in demo languages, STT, intent service, fine-tuned model integrated. M1: prepare pipeline with approval gates. M4: template review and approve screens, language selection. M2: speech steps in the flow, re-prompt fallback.
**Exit:** one campaign runs in English, Hindi, Malayalam and Tamil. Speech replies "yes", "haan", "ശരി", "ஆம்" are classified correctly in the call. Unclear speech triggers the keypad re-prompt.

### Phase 5 — Compliance and hardening (10%)
M1: privacy document, retention job, erasure, audit log checks. M2: calling approach document. M3: model report. M4: security review, backups, `ufw`, seeded second and third use cases (clinic, payment) running through the same engine.
**Exit:** checklist in section 11 complete.

### Phase 6 — Polish and demo (10%)
Seed data, rehearsed demo script, recorded fallback video of a successful live call, bug bash, slides.
**Exit:** two full rehearsals pass without intervention.

## 10. Test matrix (must pass before demo)

| # | Scenario | Expected outcome |
|---|---|---|
| 1 | Answered, presses 1 | `confirmed` |
| 2 | Answered, presses 2 | `declined` |
| 3 | Answered, presses 3 | `reschedule` |
| 4 | Presses an invalid digit twice | `unclear` |
| 5 | Answered, silence twice | `no_input`, retry scheduled |
| 6 | Hangs up during the prompt | `no_input`, `hangup_cause=caller_hangup` |
| 7 | No answer | `no_answer`, retry in 60 min |
| 8 | Busy | `busy`, retry in 30 min |
| 9 | Voicemail, policy `leave_message` | message played, outcome `voicemail`, retry in 240 min |
| 10 | Voicemail, policy `skip_and_retry` | no message, outcome `voicemail` |
| 11 | Speaks "yes" in each demo language | `confirmed` |
| 12 | Mumbles, then presses 1 | `confirmed` after one re-prompt |
| 13 | Says or presses stop | `opted_out`, never called again by any campaign |
| 14 | Calling outside the window | no calls placed until the window opens |
| 15 | Duplicate webhook delivery | no duplicate side effects |
| 16 | Worker killed mid-call | sweeper recovers the contact within 15 minutes |
| 17 | Retry non-responders button | only matching contacts re-enqueued, one extra attempt each |
| 18 | CSV with bad rows | per-row errors reported, good rows imported |

## 11. Release checklist

- [ ] All P0 requirements pass.
- [ ] Test matrix passes.
- [ ] `docs/PRIVACY.md` complete, includes provider, region, retention, erasure, third-party processors.
- [ ] `docs/CALLING_APPROACH.md` complete.
- [ ] `docs/MODEL_REPORT.md` has WER and intent F1 per language.
- [ ] No secrets in git history. `.env` not committed.
- [ ] `ufw` enabled, Postgres, Redis, AI service not reachable from the internet.
- [ ] Nightly backup verified by a restore test.
- [ ] Demo data seeded and a recorded backup demo exists.

## 12. Judging criteria mapping

| Criterion | Our answer |
|---|---|
| Ease of launching a campaign | Wizard, presets, CSV, auto translation and audio, 5 minute goal |
| Multilingual quality | Self-hosted Indic STT and translation, native-speaker review gate, per-language overrides for dates and venues |
| Intent accuracy and fallback | Rules plus fine-tuned MuRIL, confidence gate, one re-prompt, keypad fallback, `unclear` outcome |
| Real-world call behaviour | Full outcome set, AMD, retries, sweeper, idempotent webhooks |
| Dashboard | Summary, language and segment breakdowns, filters, retry, call detail |
| Privacy and compliance | Encryption, audit log, retention, erasure, consent and DND, opt-out, processing-location table |
| Generality | Four presets on one engine |

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Exotel features differ from assumptions | `CallProvider` abstraction, VERIFY list, mock first, two integration modes in `CONTRACTS.md` 8.3 |
| Speech accuracy on phone audio | 8 kHz augmentation in training and benchmarks, rules first, keypad always available, threshold tuning |
| CPU STT latency | Small model, VAD trimming, combined `/v1/speech-intent`, async fallback mode |
| Sandbox limits | Mock for volume tests, real calls only for demonstrations |
| Machine translation errors | Human approval gate, per-language overrides, protected placeholders check |
| Team merge conflicts | Directory ownership, contract-first development, small PRs |
| VPS has no GPU | CPU-friendly models, heavy work (fine-tuning, Parler pre-render) on Colab or Kaggle |
| Third-party free tier limits change | Self-hosted primary path, third parties only as fallback and documented |

## 14. Open questions for kickoff (default assumption in brackets)

1. Which Exotel features are enabled: Voicebot streaming, recording, AMD? [dynamic mode, sync speech, Exotel AMD]
2. Sandbox concurrency and allowed numbers? [3 concurrent, team phones only]
3. Languages required for the demo? [English, Hindi, Malayalam, Tamil]
4. Is self-hosted speech and language processing required or preferred? [yes, self-hosted primary]
5. Sample contact lists or templates provided? [use our fixtures]

## 15. Team and ownership summary

| Member | Role | Owns |
|---|---|---|
| Member 1 | Backend core, data and compliance | database, REST API, campaign pipeline, CSV import, analytics, crypto, audit, retention, `PRIVACY.md` |
| Member 2 | Telephony and call orchestration | providers (mock, Exotel), flow engine, webhooks, scheduler, retries, voicemail, `CALLING_APPROACH.md` |
| Member 3 | AI and language layer | AI service (STT, intent, translation, TTS), datasets, fine-tuning, benchmarks, `MODEL_REPORT.md` |
| Member 4 | Frontend, infrastructure and demo | Next.js dashboard and wizard, Compose, Caddy, VPS hardening, CI, backups, `DEMO.md` |

Dependency graph for hand-offs:

```
M3 contracts (AI API) ----> M1 ai_client, prepare pipeline
M1 schema/models --------> M2 telephony code, M4 types
M2 webhooks + public URL -> M4 (Caddy, HTTPS)
M1 REST API -------------> M4 dashboard (after MSW phase)
M3 audio + models -------> M2 speech steps
```

## 16. Glossary

- **AMD**: answering machine detection.
- **DTMF**: keypad tones.
- **IVR**: interactive voice response, scripted call flow.
- **Segment**: audience group inside a campaign (for example students, faculty).
- **Outcome**: final or latest result for a contact (see `CONTRACTS.md` section 3).
- **ExoPhone**: Exotel virtual phone number used as caller ID.
