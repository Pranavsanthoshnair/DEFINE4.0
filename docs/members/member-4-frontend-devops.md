# Member 4 — Frontend, Infrastructure and Demo

**You own:** the Next.js dashboard and campaign wizard, Docker Compose, the VPS setup and hardening, reverse proxy configuration, CI, backups, the `.env.example`, the demo script and demo data flow, and the in-app privacy page.

**Read first:** `PRD.md` and `CONTRACTS.md` (section 6 is the API you consume, section 12 is yours, section 11 you maintain).

**If you are using an AI coding agent:** give it this file plus `CONTRACTS.md`. Routes, fields and enum values are fixed by the contracts; the agent must not invent API shapes. Until the real API exists, develop against a mock server generated from the contract, then switch by an environment variable.

---

## 1. What you deliver

1. Next.js app: login, overview, templates, campaign wizard, campaign dashboard, call detail, privacy page.
2. Mock API layer (MSW) so the UI works before the backend does.
3. Docker Compose for the full stack, `.env.example`, Makefile.
4. VPS setup under a new dedicated Linux user, Caddy site config, DNS, HTTPS.
5. CI (lint, tests, build), nightly database backup and a restore test.
6. Security hardening checklist completed.
7. `docs/DEMO.md`: demo script, timing, fallback plan.

## 2. Directory ownership

```
apps/web/                     # Next.js
infra/
  caddy/pr002.caddy
  backup/{pg_backup.sh, restore_test.sh}
  deploy/{deploy.sh, bootstrap_vps.md}
docker-compose.yml, .env.example, Makefile
.github/workflows/ci.yml
docs/DEMO.md
```

## 3. Tech and libraries (frontend)

Node 20 LTS, Next.js (App Router), TypeScript strict, Tailwind CSS, shadcn/ui, TanStack Query, TanStack Table, recharts, react-hook-form with zod, papaparse (CSV preview), `date-fns`, `lucide-react`, MSW for mocks, Vitest and Testing Library, Playwright (one smoke test), ESLint and Prettier. Generate API types from `fixtures/openapi.json` (published by Member 1) with `openapi-typescript`; until it exists, hand-write types from the contract and replace them later.

API access: a single `lib/api.ts` wrapper around `fetch` that adds the bearer token, parses the error format from contract section 2, and redirects to `/login` on 401. Base URL from `NEXT_PUBLIC_API_BASE_URL`. Store the JWT in memory plus an `httpOnly` cookie set by a Next.js route handler (`/api/session`) that proxies login, so the token is not readable by scripts. If that costs too much time, fall back to `sessionStorage` and document the trade-off.

## 4. Phase plan

### Phase 0 — Setup (with everyone)
- Create the monorepo skeleton, `main` protection, PR template, CODEOWNERS (each member owns their directories).
- `docker-compose.yml` with all services from contract section 12, each running a trivial placeholder until real code lands. Healthchecks on every service. `docker compose up` must be green on your laptop and on the VPS.
- `.env.example` with every variable from contract section 11 and short comments. Add a `scripts/gen_secrets.sh` that prints random values for `JWT_SECRET`, `DATA_ENC_KEY`, `PHONE_HMAC_KEY`, `WEBHOOK_SECRET`, `AI_INTERNAL_TOKEN`, Postgres and Redis passwords.
- Makefile targets: `up`, `down`, `logs`, `migrate`, `seed`, `test`, `lint`, `fmt`, `backup`.
- CI: on each PR run ruff and pytest for Python services, ESLint, type check and Vitest for the web app, and a Docker build check.

### Phase 1 — Dashboard on mock data

Pages (App Router):

| Route | Content |
|---|---|
| `/login` | email and password form, error state |
| `/` | overview: totals across campaigns, list of recent campaigns with status badge and mini outcome bar |
| `/templates` | list, preset badge, "use this template" button |
| `/templates/[id]` | view script segments in the source language, translation status per language (Phase 4 adds editing and approval) |
| `/campaigns` | table with status, template, languages, created date, progress |
| `/campaigns/new` | wizard (below) |
| `/campaigns/[id]` | dashboard (below) |
| `/privacy` | renders the processing-location statement (static content provided by Member 1; link to the markdown) |

**Campaign wizard (`/campaigns/new`), 5 steps, state kept in one form object with zod validation per step:**
1. **Template.** Cards for the four presets and custom templates. Shows the use case and a preview of the English prompt.
2. **Event details.** Dynamic form built from the template `variables` (label, required). Fields for campaign name, organisation caller ID if needed, calling window (default 09:00 to 21:00 IST), max attempts, max concurrent calls (advanced section, collapsed by default).
3. **Languages and contacts.** Language multi-select (demo set). CSV upload with a client-side preview (first 10 rows, detected languages and segments, row count), a downloadable CSV template, and a clear note about consent and DND columns. After "Create", call the API: create campaign, then import CSV; show per-row errors in a table with row number and reason.
4. **Review.** Calls `POST prepare` and polls `GET /api/campaigns/{id}` every 3 seconds. Shows readiness per language: translation status (`draft` or `approved`), audio (`missing` or `ready`). For each language with a draft translation, show a side-by-side editor (source text left, translation right) per segment with the placeholders highlighted and non-editable tokens; buttons: Save, Regenerate, Approve. Block approval if a placeholder is missing (client check) and show server errors verbatim. Include an audio preview player for each rendered segment once ready (use the `/media/audio/{sha}.wav` URLs; the API returns them in readiness details if Member 1 adds them; otherwise skip this player).
5. **Launch.** Summary of what will happen: number of contacts, languages, window, retries. Confirmation dialog. Calls `POST launch` and redirects to the dashboard.
Wizard must be resumable: an existing draft campaign opens at the right step.

**Campaign dashboard (`/campaigns/[id]`)**
- Header: name, status badge, buttons Pause, Resume, Cancel (with confirmation), and "Retry non-responders".
- Summary cards: total contacts, attempted, answer rate, response rate, pending.
- Outcome funnel or stacked bar by outcome with a consistent colour per outcome (fixed colour map in one file; use a colour-blind-safe palette and always add text labels, never rely on colour alone).
- Two charts: **by language** and **by audience segment**, each a stacked horizontal bar of outcomes from the breakdown endpoint, with the counts in the tooltip. Clicking a bar sets the table filter to that language or segment.
- Contacts table (TanStack Table, server-side pagination): masked phone, language, segment, attempts, last outcome, next attempt time, last call time. Filters for outcome, language, segment. Clicking a row opens the call detail drawer.
- Auto refresh: poll summary every 5 s while status is `running` or `preparing`; stop when `completed`, `cancelled`.
- **Retry modal:** pre-selects the non-responder outcomes (`no_answer`, `busy`, `voicemail`, `no_input`), lets the user tick additional outcomes (`unclear`, `failed`, `call_later`), and optionally filter by language and segment. Shows the count that will be retried (use the contacts endpoint total with the same filters before submitting). Calls `POST /retry`; show the `enqueued` count in a toast.

**Call detail drawer**
- Timeline of `call_events` (time, type, short human text), captured intent(s) with source (keypad or speech), transcript if the user role allows (hidden for non-admin; show label and confidence only), duration, hangup cause.
- Recording player: only if `recording` is available; fetch with the bearer token as a blob and play with an `<audio>` element; show a notice "this access is logged".

**UX rules**
- Fully responsive down to a tablet; the demo may be on a projector, so use large readable numbers and high contrast.
- Every list has empty, loading (skeleton) and error states.
- Phone numbers are only ever shown masked as returned by the API. Never request or display unmasked numbers.
- Accessible: labels, focus rings, keyboard navigation for the wizard and tables, `aria-live` for toasts.
- Dark mode optional.

**Mocking.** MSW handlers implement every route in contract section 6 with realistic data: 3 campaigns in different statuses, 200 contacts with the full outcome mix, breakdowns that add up. Keep handlers in `apps/web/mocks/` and enable them when `NEXT_PUBLIC_USE_MOCKS=true`.

**Phase 1 exit:** every page works against MSW with no backend, Vitest covers the retry modal, the wizard step validation, and the outcome colour map.

### Phase 1 (parallel) — Infrastructure on the VPS

Do this on the VPS with a **new dedicated user** so the other project on the machine is untouched.

1. Create the user and give it SSH key access:
   ```
   sudo adduser pr002
   sudo usermod -aG docker pr002
   sudo rsync --archive --chown=pr002:pr002 ~/.ssh /home/pr002
   ```
   Verify login as `pr002` from a second terminal before closing the first session. Note: membership of the `docker` group is equivalent to root on this machine; only trusted teammates get this user, and prefer personal SSH keys over a shared password.
2. Project directory `/home/pr002/pr002`. Compose project name `pr002`, network `pr002_net`. Do not reuse other containers, volumes or ports. Check free ports with `ss -tlnp` first; use the loopback ports in contract section 12 (`127.0.0.1:8100` and `127.0.0.1:8101`) or the next free ones and update the contract if you change them.
3. DNS: A records for `api.<domain>` and `app.<domain>` pointing to the VPS public IP (a free DuckDNS subdomain works). Wait for propagation.
4. Reverse proxy: the VPS already runs Caddy as a host service. Do **not** start a second one on ports 80 or 443. Create `/etc/caddy/conf.d/pr002.caddy`:
   ```
   api.<domain> {
       reverse_proxy 127.0.0.1:8100
       encode gzip
   }
   app.<domain> {
       reverse_proxy 127.0.0.1:8101
       encode gzip
   }
   ```
   Make sure the main Caddyfile contains `import /etc/caddy/conf.d/*.caddy` (add it once, preserving existing content). Validate with `sudo caddy validate --config /etc/caddy/Caddyfile`, then `sudo systemctl reload caddy`. Caddy obtains HTTPS certificates automatically. Take a copy of the original Caddyfile before editing (`/etc/caddy/Caddyfile.bak`).
5. Add request size limit and basic headers in the `api` site block for the webhook path if needed (`request_body { max_size 1MB }` for `/webhooks/*`; `/api/campaigns/*/contacts/import` needs at least 6 MB).
6. Firewall: confirm with `sudo ufw status` that only 22, 80, 443 are allowed. Remember Docker-published ports bypass `ufw`: publish only to `127.0.0.1`, and never publish Postgres, Redis or the AI service.
7. Compose file details:
   - Postgres: image `postgres:16`, volume `pgdata`, password from env, healthcheck `pg_isready`.
   - Redis: image `redis:7`, `command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes`, volume `redisdata`, no published port.
   - `api`, `worker`, `beat`: same image from `services/api`, different `command`, `depends_on` with health conditions, `restart: unless-stopped`, shared volumes `media` and `recordings`.
   - `ai`: `services/ai` image, volume `models`, resource limits `mem_limit: 12g`, `cpus: 4`, env `OMP_NUM_THREADS=4`.
   - `web`: multi-stage Next.js standalone build.
   - Logging: `json-file` driver with `max-size: 10m` and `max-file: 5` for every service.
8. Deploy script `infra/deploy/deploy.sh`: `git pull`, `docker compose build`, `docker compose up -d`, run migrations, run health checks, print versions. Idempotent.

### Phase 2 — Public webhooks and audio
- With Member 2, verify from outside the network (a phone on mobile data) that `https://api.<domain>/media/audio/<some sha>.wav` plays, and that a request to `https://api.<domain>/webhooks/<secret>/status` returns 200 (and a wrong secret returns 404).
- Make sure the Caddy config passes through `X-Forwarded-For` and the real client IP for audit logs (default behaviour; confirm `ip` in `audit_log` is not the Docker gateway).
- Check certificate validity and the time on the VPS (`timedatectl`): clock drift breaks JWT and TLS.

### Phase 3 — Live dashboard
- Switch `NEXT_PUBLIC_USE_MOCKS=false`, point to the real API, fix every contract mismatch by reporting to Member 1 (do not work around it silently).
- Dashboard shows live changes while mock or real calls run; verify the polling cadence and that charts update without flicker.
- Implement the call detail drawer with real events and the recording player.
- Playwright smoke test: login, open a campaign, filter by language, open retry modal.

### Phase 4 — Translation review UI, multilingual display
- Template review and approve screens as specified in the wizard step 4, plus the same editor available on `/templates/[id]`.
- Render Indic scripts correctly: load a font with Devanagari, Malayalam and Tamil coverage (Noto Sans family via `next/font`), and test every demo language in the editor and tables. Right-sized line height for Indic scripts.
- Language labels in the UI show both name and native name (for example "Hindi (हिन्दी)").

### Phase 5 — Security, backups, hardening

Security checklist (tick each one and note it in `infra/deploy/bootstrap_vps.md`):
- [ ] SSH: key-only, root login disabled, password auth disabled, `fail2ban` running.
- [ ] `ufw` allows only 22, 80, 443. `ss -tlnp` shows Postgres, Redis and the AI service are bound only to the Docker network, and the api and web ports only to loopback.
- [ ] No secrets in git history (`gitleaks` scan in CI). `.env` has mode 600 and is owned by `pr002`.
- [ ] Containers run as non-root where possible.
- [ ] Unattended security upgrades enabled.
- [ ] HTTPS everywhere, HSTS header on the `app` and `api` sites.
- [ ] Rate limiting on login (done by Member 1) and a Caddy-level limit if a plugin is available; otherwise rely on the API.
- [ ] Docker log rotation configured.
- [ ] Time sync (`timedatectl` shows synchronised).

Backups:
- `infra/backup/pg_backup.sh`: `pg_dump` in custom format from the `postgres` container, encrypt with `age` or `gpg` using a key not stored on the server, write to `/home/pr002/backups/` with a timestamp, keep 7 days. Cron or a systemd timer at 02:30 IST. Also back up the `media` and `recordings` volumes weekly (recordings are encrypted already).
- `infra/backup/restore_test.sh`: restores the latest dump into a scratch database and runs a count query. Run it once and record the result.
- Copy the latest backup off the server (to a teammate's machine or another storage) before the demo.

Use cases: seed the clinic, school and payment presets (Member 1 provides them) and run one small campaign for each through the same wizard to prove generality. Take screenshots for the slides.

### Phase 6 — Demo

Write **`docs/DEMO.md`**:
1. Setup checklist for the morning of the demo (VPS healthy, services up, certificates valid, test phones charged, test numbers verified in the Exotel sandbox, volume on phones, quiet room).
2. Demo script with timings (about 7 minutes):
   1. Problem in 20 seconds.
   2. Create the seminar campaign from the preset, enter event details, upload the CSV (about a minute; speed-run the wizard).
   3. Show the translation review for Hindi, Malayalam and Tamil, approve, show audio ready.
   4. Launch. Judge or teammate phone rings: play the call on speaker, press 1 on one phone, **speak** the answer in Hindi on another, let a third go unanswered.
   5. Dashboard updates live: outcome by language and segment.
   6. Voicemail case: show (or play a recording of) a voicemail detection result.
   7. Click "Retry non-responders" and show the count.
   8. Switch to the payment preset to show generality (DTMF only, no voicemail details).
   9. Privacy page: processing-location table and retention.
   10. Close with the hybrid-approach justification in two sentences.
3. Fallback plan: (a) pre-recorded screen capture of a successful full run, (b) mock-provider run with `MOCK_SPEED=1` and the seeded `DEMO (seeded)` campaign, (c) a printed or slide version of the dashboard screenshots.
4. Talking points for likely judge questions: why hybrid, where does audio go, what if Exotel is down, how accurate is the speech, how do you handle consent and opt-out, how would it scale.
5. Who presses what (assign roles to the four members for the live demo).

Rehearse twice end to end with a timer. Record the second rehearsal as the fallback video.

## 5. Rules and pitfalls

- Never put secrets in the frontend bundle. Only `NEXT_PUBLIC_*` variables are public; the API base URL is the only one needed.
- Never display or store unmasked phone numbers. Never log them in the browser console.
- Do not call the AI service from the frontend. Everything goes through the API.
- Do not touch the other project's containers, volumes, Caddy blocks or user. Do not run commands that restart Docker or Caddy without checking they only affect this project; reloading Caddy is fine, restarting it is not needed.
- Do not publish database or Redis ports. Docker bypasses `ufw`.
- Keep the UI simple and robust over clever. A working boring dashboard beats a broken fancy one.
- Handle API errors visibly (toast plus inline), never fail silently.
- Poll sensibly: stop polling when the tab is hidden (`document.visibilityState`) and when the campaign is finished.
- Commit lockfiles. Pin base image tags (no `latest`).

## 6. Hand-offs

| To or from | What | When |
|---|---|---|
| from M1 | `fixtures/openapi.json`, example responses | early Phase 1 |
| to all | working `docker compose up`, `.env.example`, deploy instructions | end of Phase 0 |
| to M2 | public HTTPS URLs for webhooks and audio | start of Phase 2 |
| from M3 | AI container resource needs, volume paths and download script | Phase 0 and 5 |
| from M1 | final privacy text for `/privacy` | Phase 5 |
| to all | demo schedule, roles, rehearsal times | Phase 6 |

## 7. Definition of done checklist

- [ ] `docker compose up` brings up all services healthy on the VPS under the `pr002` user.
- [ ] HTTPS dashboard reachable at `app.<domain>`, API at `api.<domain>`.
- [ ] Wizard works end to end with the real API for four languages.
- [ ] Dashboard shows summary, by-language and by-segment charts, contacts table with filters, retry modal, call detail drawer.
- [ ] Mocks and real API both work (switchable by env var).
- [ ] Security checklist ticked.
- [ ] Backup and restore tested; a copy exists off-server.
- [ ] Three use-case presets demonstrated through the same UI.
- [ ] `docs/DEMO.md` written; two rehearsals done; fallback video recorded.
