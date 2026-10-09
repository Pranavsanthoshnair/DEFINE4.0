# Veylo — Deployment Guide

## Architecture

```
Browser
  -> Vercel (Next.js frontend)
      -> Render: veylo-backend (FastAPI, port $PORT)
          -> Supabase PostgreSQL (database + auth)
          -> Render: veylo-ai (FastAPI AI service, port $PORT)
              -> Sarvam AI API (STT, TTS, Translate)
              -> Groq API (Whisper STT fallback)
          -> Exotel API (outbound calling)
              -> Exotel webhook -> veylo-backend /api/v1/webhooks/exotel
```

---

## 1. Supabase Setup

### 1.1 Create project
1. Go to [supabase.com](https://supabase.com) → New Project
2. Choose region closest to your Render region (Oregon → US West)
3. Note: `Project URL`, `anon key`, `service_role key`, `database password`

### 1.2 Run migrations
```bash
# From repo root
cd backend
# Apply all migration files in order
# (migrations live in backend/alembic/versions/ or backend/migrations/)
alembic upgrade head
```

If Alembic is not configured, run the SQL files in `backend/migrations/` manually in the Supabase SQL Editor.

### 1.3 Connection string
Use the **connection pooler** URL from Supabase → Settings → Database → Connection Pooling:
```
postgresql+asyncpg://postgres.xxxx:password@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
```

---

## 2. Deploy AI Service to Render

### 2.1 Create Web Service
- **Root Directory:** `ai`
- **Runtime:** Python
- **Build Command:** `pip install -e ".[test]"`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path:** `/healthz`

### 2.2 Set Environment Variables
| Variable | Value |
|---|---|
| `AI_STUB` | `false` |
| `STT_PROVIDER` | `auto` |
| `SARVAM_API_KEY` | your Sarvam key |
| `GROQ_API_KEY` | your Groq key |
| `INTERNAL_TOKEN` | generate a strong random token (must match backend `AI_INTERNAL_TOKEN`) |
| `LLM_FALLBACK` | `none` |

### 2.3 Note the deployed URL
```
https://veylo-ai.onrender.com   (example — use your actual URL)
```

---

## 3. Deploy Backend to Render

### 3.1 Create Web Service
- **Root Directory:** `backend`
- **Runtime:** Python
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path:** `/health`

### 3.2 Set Environment Variables
| Variable | Value |
|---|---|
| `ENVIRONMENT` | `production` |
| `DEBUG` | `false` |
| `PUBLIC_BASE_URL` | `https://veylo-backend.onrender.com` |
| `CORS_ORIGINS` | `["https://your-app.vercel.app"]` |
| `WEB_ORIGIN` | `https://your-app.vercel.app` |
| `DATABASE_URL` | Supabase pooler connection string |
| `SUPABASE_URL` | from Supabase dashboard |
| `SUPABASE_ANON_KEY` | from Supabase dashboard |
| `SUPABASE_SERVICE_ROLE_KEY` | from Supabase dashboard |
| `SECRET_KEY` | generate strong random |
| `JWT_SECRET` | generate strong random |
| `WEBHOOK_SECRET` | generate strong random 32-char string |
| `CALL_PROVIDER` | `exotel` |
| `EXOTEL_SID` | from Exotel dashboard |
| `EXOTEL_API_KEY` | from Exotel dashboard |
| `EXOTEL_API_TOKEN` | from Exotel dashboard |
| `EXOTEL_SUBDOMAIN` | `api.exotel.com` (or region subdomain) |
| `EXOTEL_CALLER_ID` | your verified Exotel number |
| `WEBHOOK_BASE_URL` | `https://veylo-backend.onrender.com` |
| `AI_BASE_URL` | `https://veylo-ai.onrender.com` |
| `AI_INTERNAL_TOKEN` | same token set in AI service `INTERNAL_TOKEN` |
| `MEDIA_DIR` | `/tmp/media` |
| `RECORDINGS_DIR` | `/tmp/recordings` |

### 3.3 Verify backend health
```
curl https://veylo-backend.onrender.com/health
# Expected: {"status":"ok","version":"0.1.0"}
```

---

## 4. Configure Exotel Webhooks

In your Exotel dashboard, set these callback URLs:

| Event | URL |
|---|---|
| Call status callback | `https://veylo-backend.onrender.com/api/v1/webhooks/exotel` |
| DTMF / keypad input | `https://veylo-backend.onrender.com/api/v1/webhooks/exotel/dtmf` |
| Voicemail callback | `https://veylo-backend.onrender.com/api/v1/webhooks/exotel/voicemail` |

> Check `backend/app/api/routes/webhooks.py` for the exact implemented paths.

---

## 5. Deploy Frontend to Vercel

### 5.1 Import repository
1. Go to [vercel.com](https://vercel.com) → New Project → Import Git Repository
2. Select `Pranavsanthoshnair/DEFINE4.0`

### 5.2 Configure project settings
| Setting | Value |
|---|---|
| **Root Directory** | `frontend` |
| **Framework Preset** | Next.js |
| **Build Command** | `npm run build` (auto-detected) |
| **Output Directory** | `.next` (auto-detected) |
| **Node.js Version** | 20.x |

### 5.3 Set Environment Variables (in Vercel dashboard)
| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://veylo-backend.onrender.com` |
| `NEXT_PUBLIC_SUPABASE_URL` | your Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | your Supabase anon key |

### 5.4 Deploy and note the URL
```
https://veylo-xxxx.vercel.app   (example — use your actual URL)
```

### 5.5 Update backend CORS with final Vercel URL
In Render → veylo-backend → Environment Variables, update:
```
CORS_ORIGINS=["https://veylo-xxxx.vercel.app"]
WEB_ORIGIN=https://veylo-xxxx.vercel.app
```
Then redeploy the backend.

---

## 6. Verification Checklist

```
[ ] GET https://veylo-backend.onrender.com/health → {"status":"ok"}
[ ] GET https://veylo-ai.onrender.com/healthz     → {"status":"ok","models":{...}}
[ ] Frontend loads at Vercel URL without console errors
[ ] Login / signup works (Supabase auth)
[ ] Create a campaign in the UI
[ ] AI service STT responds (test via stt_benchmark.py)
[ ] Exotel test call initiated (1 authorised test number only)
[ ] Webhook received and persisted in Supabase
[ ] Dashboard shows updated call status
```

---

## 7. Security Notes

- `SUPABASE_SERVICE_ROLE_KEY` — backend only, never in frontend
- `EXOTEL_API_KEY` / `EXOTEL_API_TOKEN` — backend only
- `SARVAM_API_KEY` / `GROQ_API_KEY` — AI service only
- `AI_INTERNAL_TOKEN` — shared between backend and AI service, not exposed publicly
- No secrets in `NEXT_PUBLIC_*` variables
- CORS restricted to exact Vercel origin in production

---

## 8. Rollback

### Render
- Every deploy creates a snapshot
- Go to Render → Service → Deploys → click any past deploy → **Rollback**

### Vercel
- Go to Vercel → Project → Deployments → find last good deploy → **Promote to Production**

### Database
- Never run destructive migrations without a Supabase backup
- Supabase → Settings → Backups to restore a point-in-time snapshot

---

## 9. Local Development

```bash
# AI service
cd ai
cp .env.example .env   # fill in keys
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[test]"
uvicorn app.main:app --port 8200 --reload

# Backend
cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --port 8000 --reload

# Frontend
cd frontend
cp .env.example .env.local
npm install
npm run dev
```
