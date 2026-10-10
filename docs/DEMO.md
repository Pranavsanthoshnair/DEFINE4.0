# Demo Script

**Veylo · DEFINE 4.0 · PR 002 · ~7 minutes**

## Role Assignments

| Role | Person |
|---|---|
| Driver (types/clicks) | TBD |
| Narrator | TBD |
| Backup (recordings, fallbacks) | TBD |

---

## The Pitch (0:00 – 0:30)

> "Veylo is a multilingual outbound calling platform that learns when to reach each person, and keeps its privacy promises even after someone is erased. Three pillars: LEARNS, PROTECTS, PROVES."

Show the homepage. Point to the three pillars on screen.

---

## Step 1 — Create Campaign and Show Multilingual Audio (0:30 – 1:30)

1. Click **+ Quick Campaign** → name it "Seminar Demo"
2. Show the language selector — pick Hindi or Tamil
3. Click **🎙 Prepare Audio** — audio segments generate (ElevenLabs)
4. Say: *"Every segment is pre-rendered in the contact's language before the call begins. Zero latency when they pick up."*

**If ElevenLabs fails:** show a pre-recorded audio clip from `docs/demo-assets/`.

---

## Step 2 — Preflight Check (1:30 – 2:00)

Open `https://vaylo-aeta.onrender.com/docs` → `GET /api/v1/campaigns/{id}/preflight`

Say: *"Launch is blocked until every check passes — contacts loaded, audio ready, caller ID configured, webhook reachable."*

Show the JSON response with all green checks.

---

## Step 3 — Live Call (2:00 – 2:30)

1. Add your own phone number as a contact
2. Click **🚀 Launch**
3. Phone rings — pick up, press 1
4. Say: *"That was Exotel placing the call, ElevenLabs voice playing the greeting, and our webhook capturing the response."*

**If call doesn't come:** play the pre-recorded demo video at `docs/demo-assets/call-demo.mp4`.

---

## Step 4 — Simulation: Fixed vs Adaptive (2:30 – 3:30)

Open `https://vaylo-aeta.onrender.com/docs` → `GET /api/v1/simulation/run`

Or show the Analytics page with the simulation chart.

Say: *"This is SIMULATED — 20 seeds, 150 synthetic contacts, students peak evenings, faculty peak midday. The adaptive scheduler picks up X% more contacts by round 4 vs fixed. The seeds and population parameters are in the repo."*

Point to `structured_population.adaptive_better_in_seeds` — e.g. "17 out of 20 seeds, adaptive wins."

---

## Step 5 — Negative Control (H19) (3:30 – 4:00)

Still on the simulation response. Point to `control_population`.

Say: *"Same algorithm, flat pickup probability — no time-of-day pattern. The adaptive engine shows no meaningful gain. This proves the improvement in the structured population comes from learning, not from a rigged simulation. Most teams don't show you where their feature doesn't help."*

---

## Step 6 — Opt Out → Erase → Re-import Blocked (H2) (4:00 – 4:45)

1. Go to Audience & Contacts
2. Delete the contact (opted-out) — show the response: *"Contact deleted and phone added to suppression filter"*
3. Try to re-import a CSV with the same number
4. Show it's rejected: *"Contact is suppressed"*

Say: *"The phone is stored as a keyed HMAC hash in a Bloom filter — never the number itself. Zero false negatives. The list is gone; the promise isn't."*

---

## Step 7 — Data Map and Audit Chain (5:30 – 6:15)

Show `docs/PRIVACY.md` in the browser (or the privacy page if built).

Say: *"Every data category, where it's processed, which third party, retention, and deletion. Exotel carries call audio — we say so. ElevenLabs gets script text only, no personal data. Everything else runs on our own infrastructure."*

Show `GET /admin/audit/verify` → chain passes. Say: *"Tamper-evident, not tamper-proof. We say that too."*

---

## Step 8 — Close (6:15 – 7:00)

Show `docs/CALLING_APPROACH.md` — the three-approach comparison table.

> "Veylo learns when to reach people, protects them even after erasure, and proves every claim with evidence a judge can check. Seeds in the repo, parameters published, limitations stated. Thank you."

---

## Fallbacks

| What breaks | Fallback |
|---|---|
| Exotel call doesn't ring | Play `docs/demo-assets/call-demo.mp4` |
| ElevenLabs 401 | Show pre-generated audio clips, explain key rotation |
| Backend 503 | Use local dev server with `.env` credentials |
| Simulation endpoint fails | Show static chart image from `docs/demo-assets/simulation-chart.png` |

## Rehearsal Checklist

- [ ] Full run-through without intervention (rehearsal 1)
- [ ] Full run-through without intervention (rehearsal 2)  
- [ ] Pre-render all audio for demo campaign
- [ ] Record backup video of successful call
- [ ] Export simulation chart as static image
- [ ] Verify `EXOTEL_CALLER_ID` is correct ExoPhone
- [ ] Verify `WEBHOOK_BASE_URL=https://vaylo-aeta.onrender.com`
- [ ] Verify `ELEVENLABS_API_KEY` is valid
