# Veylo — Repo State Audit (Task A)

**Date & Time:** 2026-10-09  
**Branch:** `main`  
**Git Commit Baseline:** `98f17bb` (`main`)

---

## 1. Executive Summary & Decisions Settlement

1. **D1 (Data Stack):** **SETTLED.** Fully transitioned to self-hosted PostgreSQL via SQLAlchemy 2.0 (`app/db/models.py`, `app/db/session.py`) and JWT auth (`app/security/auth.py`). Supabase dependencies have been decoupled from the backend.
2. **D2 (Task Queue):** **SETTLED.** Celery + Redis initialized (`app/celery_app.py`).
3. **D3 (Languages):** English (`en`), Hindi (`hi`), Malayalam (`ml`), Tamil (`ta`).
4. **D4 (Keypad Map):** `1` confirm, `2` decline, `3` reschedule, `0` repeat, `8` change language, `9` stop calling. Fully implemented in `telephony/flow/engine.py`.

---

## 2. Comprehensive Task Audit (Tasks 0 to 16)

| Task | Name | Status | Key Existing Files | Tests Passing | Gaps / Actions Needed |
|---|---|---|---|---|---|
| **Task A** | Repo State Audit | **DONE** | `AUDIT.md` | 67 backend tests pass | Initial baseline mapped. |
| **Task 0** | Foundation & Config | **PARTIAL** | `backend/app/core/config.py`, `docker-compose.yml`, `requirements.txt` | `test_health.py` (3/3 pass) | Add explicit `Clock` interface (`core/clock.py`), add blueprint env keys (`BLOOM_HMAC_KEY`, `MASTER_KEK`, etc.). |
| **Task 1** | DB Models & Migrations | **DONE / PARTIAL** | `backend/app/db/models.py`, `alembic/` | DB schema passes validation | Add blueprint tables (`slot_stats`, `contact_slot_stats`, `retry_decisions`, `suppression_layers`, `erasure_ledger`, `audit_log.prev_hash/row_hash`). |
| **Task 2** | Crypto & Envelope Shredding (H3) | **PARTIAL** | `backend/app/security/crypto.py` | Unit crypto passes | Implement separate KeyStore (`put_key`, `get_key`, `shred`) and `replay_erasure_ledger()`. |
| **Task 3** | Keyed Scalable Bloom Filter (H2) | **NOT STARTED** | `backend/app/security/suppression.py` | — | Implement Scalable Bloom filter with `BLOOM_HMAC_KEY`, double hashing, and persistence. |
| **Task 4** | Hash-Chained Audit Trail (H4) | **PARTIAL** | `backend/app/security/audit.py` | Audit writer passes | Add SHA256 `prev_hash`/`row_hash` linkage and `GET /api/v1/admin/audit/verify`. |
| **Task 5** | Retry Policy & Window Math | **DONE** | `backend/app/telephony/retry.py` | `test_retry.py` (14/14 pass) | Fixed mode reproduces PRD §10 timings (60/30/240m). |
| **Task 6** | Adaptive Scheduler (H1) | **NOT STARTED** | `backend/app/campaigns/adaptive_scheduler.py` | — | Thompson sampling Beta–Bernoulli slot optimizer with segment shrinkage and explainability tooltips. |
| **Task 7** | Provider Interface & Mock | **DONE** | `telephony/providers/` (`base.py`, `mock.py`, `exotel.py`) | `test_mock_provider.py` (12/12 pass) | Mock provider passes CONTRACTS scenarios. |
| **Task 8** | CSV Import & Contacts | **PARTIAL** | `campaigns/csv_import.py`, `api/routes/contacts.py` | CSV import functional | Integrate suppression filter checks and DEK per-contact encryption. |
| **Task 9** | Call Flow Engine | **DONE** | `telephony/flow/engine.py` | `test_flow_engine.py` (34/34 pass) | DTMF keypad mapping, voicemail policy, and fallback chains passing. |
| **Task 10** | Scheduler, Workers & Sweeper | **PARTIAL** | `telephony/scheduler.py`, `tasks.py` | Scheduler loop exists | Periodic due-contact dispatch and 15m stuck-call sweeper. |
| **Task 11** | Simulation Harness (H14, H19) | **NOT STARTED** | `backend/app/analytics/simulation.py` | — | 20-seed comparison on structured population vs negative control. |
| **Task 12** | Analytics & Small-Cell (H7) | **PARTIAL** | `analytics/queries.py`, `analytics/router.py` | Basic metrics exist | Add small-cell suppression ($k < 5$) with differencing protection. |
| **Task 13** | Preflight & Preview Call (H8, H9) | **PARTIAL** | `campaigns/service.py` | Basic campaign logic exists | Add `GET /campaigns/{id}/preflight` and `POST /campaigns/{id}/preview-call`. |
| **Task 14** | AI Layer (TTS/STT/Intent) | **PARTIAL** | `ai/app/`, `ai/models.yaml` | 38/44 pass (Groq/Sarvam switch) | Fix STT fallback mock switch and add deterministic date/time renderer (`H5a`). |
| **Task 15** | Frontend UI & Polish | **DONE** | `frontend/src/app/`, `components/ui/interactive/` | Builds cleanly (18/18 routes) | Connected interactive client components, 3D motion transitions, and high-contrast styling. |
| **Task 16** | Evidence Pack Documentation (H20) | **PARTIAL** | `docs/` (`CALLING_APPROACH.md`, `PRIVACY.md`, `MODEL_REPORT.md`, `DEMO.md`) | Basic skeletons exist | Fill in empirical benchmarks, privacy architecture data map, and demo script. |

---

## 3. Immediate Implementation Sequence (Skipping Done Tasks)

1. **Task 0 & Task 1 (Blueprint Schema Updates & Clock):** Add `core/clock.py`, blueprint tables (`suppression_layers`, `slot_stats`, `contact_slot_stats`, `retry_decisions`, `erasure_ledger`) to models and migration.
2. **Task 3 (Suppression Filter - H2):** Implement `app/security/suppression.py` (Keyed Scalable Bloom Filter).
3. **Task 4 (Hash-Chained Audit Trail - H4):** Implement SHA256 chain in `app/security/audit.py` + verify route.
4. **Task 2 (Crypto KeyStore & Shredding - H3):** Implement `app/security/keystore.py` & erasure replay.
5. **Task 6 (Adaptive Scheduler - H1):** Implement `app/campaigns/adaptive_scheduler.py` (Thompson Sampling).
6. **Task 11 (Simulation & Negative Control - H14/H19):** Implement `app/analytics/simulation.py`.
7. **Task 12 (Small-Cell Suppression - H7) & Task 13 (Preflight & Preview - H8/H9).**
8. **Task 14 (Deterministic Date/Number Renderer - H5a).**
9. **Task 16 (Evidence Pack Documentation).**
