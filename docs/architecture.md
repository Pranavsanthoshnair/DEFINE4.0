# Veylo — Architecture

## Overview

Veylo is a monorepo containing a **Next.js frontend** and a **FastAPI backend**, connected through a centralised typed API client. Supabase provides PostgreSQL, auth, and realtime. Exotel handles telephony.

---

## System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser                                  │
│  Next.js (Vercel)   ←→   api-client.ts  ──→  FastAPI Backend   │
└───────────────────────────────────────────────────────┬─────────┘
                                                        │
               ┌────────────────────────────────────────┤
               │                                        │
        ┌──────┴──────┐                     ┌───────────┴──────────┐
        │  Supabase   │                     │     Exotel API        │
        │  PostgreSQL │                     │  (outbound calls)     │
        └─────────────┘                     └──────────────────────┘
                                                        │
                                               Webhook callback
                                             (POST /api/v1/webhooks/
                                              exotel/call-status)
```

---

## Responsibility Split

| Layer | Owns |
|-------|------|
| Frontend | UI, routing, form validation (Zod), API calls via api-client.ts |
| Backend | Campaign execution, call initiation, webhook processing, retry logic, AI generation, analytics aggregation |
| Supabase | Auth (JWT), PostgreSQL storage, Row-Level Security |
| Exotel | PSTN call delivery, call status callbacks |

**Secrets rule:** Exotel credentials and AI API keys exist only in backend `.env`. Frontend only holds the Supabase anon key and the backend base URL.

---

## Domain Models

### Campaign
Represents a calling campaign created by an organisation. Owns configuration, script, and language settings.

### CampaignScript
Stores the AI-generated (or manually edited) call script for one language variant of a campaign.

### Contact
A raw contact record (name, phone, preferred language).

### CampaignRecipient
Links a Contact to a Campaign for a specific run. Owns the **recipient outcome** — this is separate from individual call attempt statuses and is updated when a definitive outcome is known.

### CallAttempt
One technical dial attempt. May succeed, fail, or time out. Stored immutably; outcome is never overwritten.

### CallEvent
Raw webhook event received from Exotel. Processed idempotently using `CallSid` as the deduplication key.

### AuditLog
Append-only record of all state transitions (campaign launched, paused, recipient outcome changed, etc.).

---

## Data Flow — Outbound Call

```
1. Operator launches campaign (POST /api/v1/campaigns/{id}/launch)
2. CampaignService iterates CampaignRecipients with outcome=pending
3. ExotelService.initiate_call(phone, call_flow_id) → Exotel API
4. CallAttempt row created with status=initiated
5. Exotel dials the number
6. Exotel POSTs call-status webhook → /api/v1/webhooks/exotel/call-status
7. WebhookHandler deduplicates on CallSid, creates CallEvent
8. CallAttempt status updated
9. If answered: CampaignRecipient.outcome updated to answered
10. If no-answer/busy: RetryService.should_retry() evaluated
11. If retry: next attempt scheduled
```

---

## Key Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| Business logic in services, not routes | Routes stay thin; services are independently testable |
| Idempotent webhook processing | Exotel may deliver the same event multiple times |
| CampaignRecipient outcome ≠ CallAttempt status | A recipient may have multiple failed attempts before a successful one |
| Provider abstraction for AI | Swap OpenAI → Gemini → Anthropic by changing one env var |
| Centralised api-client.ts | All backend calls go through one module — easy to add auth headers, retry logic, error normalisation |

---

## Deployment

| Service | Platform |
|---------|----------|
| Frontend | Vercel (auto-deploys on push to `main`) |
| Backend | Render / Railway (Dockerfile or `uvicorn` start command) |
| Database | Supabase managed PostgreSQL |
| Webhooks | Public backend URL required for Exotel callbacks |
