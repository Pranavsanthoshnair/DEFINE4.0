# Veylo

> AI-assisted multilingual calling campaign platform — DEFINE 4.0 Hackathon

Veylo helps organisations create, launch, monitor, and analyse outbound calling campaigns. Turn a campaign brief into a validated calling workflow, connect each call response to a clear next action, and track every outcome with traceable evidence.

---

## Quick Start

### Prerequisites

| Tool | Minimum version |
|------|----------------|
| Node.js | 20.x |
| npm | 10.x |
| Python | 3.11 |
| pip | 24.x |

---

### 1 — Clone the repo

```bash
git clone <repository-url>
cd DEFINE4.0
```

---

### 2 — Backend setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and edit environment variables
copy .env.example .env   # Windows
# cp .env.example .env   # macOS / Linux
# → Fill in SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, EXOTEL_*, AI_API_KEY

# Run the dev server
uvicorn app.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs  
Health check: http://localhost:8000/health

---

### 3 — Frontend setup

```bash
cd frontend

# Install dependencies
npm install

# Copy and edit environment variables
copy .env.example .env.local   # Windows
# cp .env.example .env.local   # macOS / Linux
# → Set NEXT_PUBLIC_API_URL=http://localhost:8000
# → Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY

# Run the dev server
npm run dev
```

App available at: http://localhost:3000

---

## Project Structure

```
DEFINE4.0/
├── frontend/          Next.js 16 + TypeScript + Tailwind CSS
│   └── src/
│       ├── app/       App Router pages (dashboard, campaigns, contacts, analytics)
│       ├── components/layout/ and campaigns/
│       ├── lib/       api-client.ts, supabase.ts, utils.ts
│       └── types/     Shared TypeScript domain types
├── backend/           FastAPI + Python 3.11
│   └── app/
│       ├── main.py    Application factory + CORS
│       ├── core/      config.py, security.py
│       ├── api/routes/ health, campaigns, contacts, calls, analytics, webhooks
│       ├── services/  campaign, exotel, ai, retry, analytics
│       └── tests/     Smoke tests
├── docs/              architecture.md, api.md
└── .gitignore
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing secret |
| `CORS_ORIGINS` | JSON array of allowed frontend origins |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service-role key (backend only) |
| `DATABASE_URL` | PostgreSQL connection string |
| `EXOTEL_SID` | Exotel account SID |
| `EXOTEL_API_KEY` | Exotel API key |
| `EXOTEL_API_TOKEN` | Exotel API token |
| `EXOTEL_CALLER_ID` | Exotel virtual number |
| `AI_PROVIDER` | `openai` \| `anthropic` \| `gemini` |
| `AI_API_KEY` | LLM provider API key |
| `WEBHOOK_BASE_URL` | Public URL for Exotel callbacks |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend base URL |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon/public key |

---

## Running Tests

### Backend

```bash
cd backend
pytest tests/ -v
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |
| Backend | FastAPI, Python 3.11, Pydantic v2 |
| Database / Auth | Supabase (PostgreSQL) |
| Telephony | Exotel API + webhooks |
| AI | OpenAI / Anthropic / Gemini (provider abstraction) |
| Deployment | Vercel (frontend), Render / Railway (backend) |

---

## Implementation Status

| Feature | Status |
|---------|--------|
| Project structure & architecture | ✅ Done |
| Frontend shell (landing, dashboard, campaigns, contacts, analytics) | ✅ Done |
| Backend health endpoint | ✅ Done |
| Campaign CRUD stubs | ✅ Stub |
| Contact import stubs | ✅ Stub |
| Supabase integration | 🔲 Pending |
| AI script generation | 🔲 Pending |
| Exotel call initiation | 🔲 Pending |
| Webhook processing | 🔲 Pending |
| Retry logic | 🔲 Pending |
| Analytics aggregation | 🔲 Pending |
| Campaign creation wizard UI | 🔲 Pending |
| Live campaign monitoring UI | 🔲 Pending |

---

## Team

| Name | Role |
|------|------|
| — | — |

DEFINE 4.0 — The World's Realest Hackathon
