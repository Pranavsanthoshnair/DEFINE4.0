# docs/DEMO.md — Veylo PR 002 Demo Script
# Owner: Member 4 | Updated: October 2026

## 1. Morning-of-demo checklist (run 2 hours before)

### VPS
- [ ] `docker compose ps` — all services show **healthy**
- [ ] `curl -fsS https://api.<domain>/healthz` returns OK
- [ ] `curl -fsS https://app.<domain>/` returns HTTP 200
- [ ] Certificate valid, time synced: `timedatectl` shows "synchronized: yes"
- [ ] At least 10 GB disk free: `df -h /`

### Database
- [ ] Seed demo data: `docker compose exec api python -m app.db.seed_demo`
- [ ] 3 campaigns: clinic (running), school (completed), seminar (draft)
- [ ] 200 contacts in clinic with mixed outcomes

### Telephony
- [ ] Exotel sandbox active and API keys valid
- [ ] Test phones charged, numbers added to Exotel sandbox:
  - Phone A (Member 2): will press 1 (DTMF confirm)
  - Phone B (Member 3): will speak intent in Hindi
  - Phone C: unattended -> voicemail
- [ ] Volume at maximum, quiet room confirmed

### Presentation
- [ ] Fallback screen recording ready (`docs/demo_recording.mp4`)
- [ ] Slides with dashboard screenshots ready
- [ ] Browser open at login URL, credentials ready
- [ ] Laptop mirrored to projector and tested

---

## 2. Demo script (~7 minutes)

### Member roles
| Member | Role |
|---|---|
| Member 4 | Drives laptop and dashboard |
| Member 1 | Narrates, answers questions |
| Member 2 | Phone A: press 1 (DTMF confirm) |
| Member 3 | Phone B: speak intent in Hindi |

### 2.1 Problem (20 s)
"Every year, 500 institutions spend days on manual calling, reach under 30% of contacts, and collect no structured data. Veylo automates the entire flow with a single CSV upload."

### 2.2 Create the seminar campaign (60 s)
1. Log in -> New Campaign
2. Step 1 Template: select "Seminar Invitation" preset, show English script preview
3. Step 2 Event details: "Live Demo - Seminar 2026", calling window 09:00-21:00
4. Step 3 Languages + Contacts: select EN, HI, ML, TA; upload contacts_sample.csv; show 20-row preview with consent and DND columns
5. Click Create: show result "20 imported, 0 errors"

### 2.3 Translation review (60 s)
6. Wizard auto-advances to Review; POST prepare fires; polls every 3 s
7. Show readiness: Hindi/Malayalam/Tamil -> draft translation, audio missing
8. Open Hindi side-by-side editor: {event_name} token highlighted, non-editable
9. Approve Hindi -> audio renders (green tick)
10. Approve Malayalam and Tamil

### 2.4 Launch (15 s)
11. Launch tab: 20 contacts, 4 languages, 3 max attempts
12. Click Launch -> confirm -> redirect to campaign dashboard

### 2.5 Live calls (90 s)
13. Dashboard shows "running", auto-refreshes every 5 s
14. Phone A rings -> presses 1 -> outcome "confirmed" appears
15. Phone B rings -> speaks Hindi -> STT captures intent -> "confirmed"
16. Phone C no answer -> voicemail -> show "voicemail" outcome
17. Point to by-language stacked bar showing EN, HI, ML, TA with outcome breakdown

### 2.6 Retry non-responders (30 s)
18. Click Retry non-responders
19. Modal pre-selects: no_answer, busy, voicemail, no_input
20. Shows count "3 contacts will be retried"
21. Click Retry -> toast "3 contacts enqueued"

### 2.7 Payment preset (20 s)
22. Open pre-seeded "School Payment Reminder" (completed)
23. Show DTMF-only flow, by-segment chart: students vs faculty
24. "Same wizard, same dashboard, different use case."

### 2.8 Privacy page (15 s)
25. Click Privacy in sidebar
26. Processing Location table: "All data stays in India. Only E.164 number to Exotel."
27. Retention: recordings 30 days, events 90 days, contacts on organiser request

### 2.9 Close (20 s)
"Veylo is hybrid: deterministic DTMF for precision, AI speech for richer intent in regional languages. All models run on-premise. No contact data leaves the server except the phone number to Exotel, an Indian provider."

---

## 3. Fallback plan

| Scenario | Fallback |
|---|---|
| Live call fails (Exotel down) | Switch to CALL_PROVIDER=mock MOCK_SPEED=1; restart api + worker; run pre-seeded "DEMO (seeded)" campaign |
| Dashboard fails to load | Play pre-recorded screen capture (docs/demo_recording.mp4) |
| VPS unreachable | npm run dev locally with NEXT_PUBLIC_USE_MOCKS=true; demo on MSW mock data |
| All digital fails | Printed / slide dashboard screenshots; narrate the flow |

Record a clean full run before demo day. Save as docs/demo_recording.mp4 and upload to shared Google Drive.

---

## 4. Judge Q&A talking points

**Why hybrid (DTMF + speech)?**
DTMF is 100% reliable across all phone types. Speech adds richer intent for regional languages where typing is cumbersome. Users choose - neither is forced.

**Where does audio go?**
TTS audio stays on the VPS. Call recordings are AES-256-GCM encrypted before write, admin-only for playback, deleted after 30 days.

**What if Exotel is down?**
Mock provider covers the demo. In production, calls retry within the calling window; a circuit breaker pauses after 10 consecutive failures.

**How accurate is the speech?**
Faster-Whisper (small) on 8 kHz telephony achieves approximately 85% WER for Indian English and Hindi in quiet conditions. A secondary LLM intent layer abstracts away transcription errors.

**How do you handle consent and opt-out?**
consent=true is required at CSV import. DND list checked at import. Mid-call opt-out flags the contact immediately. Erasure is a single API call that nulls the record and deletes recordings.

**How would it scale?**
Celery workers are stateless - scale horizontally. Token-bucket rate limiter in Redis respects Exotel concurrent limits. Postgres read replica for analytics. CDN for audio assets.

---

## 5. Rehearsal log

| Run | Date | Duration | Issues found | Fixed? |
|---|---|---|---|---|
| Rehearsal 1 | TBD | | | |
| Rehearsal 2 (recorded) | TBD | | | |

Rehearse twice end-to-end with a timer. Record the second rehearsal as the fallback video.
