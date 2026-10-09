-- Veylo — Supabase SQL Schema
-- Run this in: Supabase Dashboard → SQL Editor → New Query
-- Project: mmhsjabzjlfpagdhxrcs

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── campaigns ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS campaigns (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL CHECK (char_length(name) BETWEEN 1 AND 200),
    description TEXT,
    language    VARCHAR(2) NOT NULL DEFAULT 'en',
    brief       TEXT,
    status      TEXT NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft','scheduled','running','paused','completed','cancelled')),
    created_by  UUID,
    scheduled_at TIMESTAMPTZ,
    window_start TIME,
    window_end   TIME,
    max_retries  INTEGER NOT NULL DEFAULT 2,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_campaigns_status ON campaigns(status);
CREATE INDEX IF NOT EXISTS ix_campaigns_created_at ON campaigns(created_at DESC);

-- ── contacts ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS contacts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_enc       TEXT NOT NULL,         -- hex-encoded encrypted phone
    phone_hash      VARCHAR(64) NOT NULL UNIQUE,
    phone_last4     VARCHAR(4) NOT NULL,
    name_enc        TEXT,                  -- hex-encoded encrypted name
    language        VARCHAR(2) NOT NULL DEFAULT 'en',
    segment         TEXT,
    consent         BOOLEAN NOT NULL DEFAULT TRUE,
    consent_source  TEXT,
    consent_at      TIMESTAMPTZ,
    dnd             BOOLEAN NOT NULL DEFAULT FALSE,
    opted_out       BOOLEAN NOT NULL DEFAULT FALSE,
    opted_out_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_contacts_phone_hash ON contacts(phone_hash);

-- ── campaign_contacts ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS campaign_contacts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    contact_id      UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','queued','calling','completed','failed','suppressed')),
    outcome         TEXT,
    attempt_count   INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(campaign_id, contact_id)
);

CREATE INDEX IF NOT EXISTS ix_cc_campaign_id ON campaign_contacts(campaign_id);
CREATE INDEX IF NOT EXISTS ix_cc_status ON campaign_contacts(status);

-- ── calls ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS calls (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id         UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    campaign_contact_id UUID REFERENCES campaign_contacts(id) ON DELETE SET NULL,
    provider_call_sid   TEXT,
    status              TEXT NOT NULL DEFAULT 'queued'
                        CHECK (status IN ('queued','ringing','in_progress','completed','busy','no_answer','failed','cancelled','error')),
    direction           TEXT NOT NULL DEFAULT 'outbound',
    language            VARCHAR(2),
    duration_s          INTEGER,
    outcome             TEXT,
    recording_url       TEXT,
    cost_usd            NUMERIC(10,6),
    started_at          TIMESTAMPTZ,
    answered_at         TIMESTAMPTZ,
    ended_at            TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_calls_campaign_id ON calls(campaign_id);
CREATE INDEX IF NOT EXISTS ix_calls_provider_call_sid ON calls(provider_call_sid);
CREATE INDEX IF NOT EXISTS ix_calls_status ON calls(status);

-- ── call_events ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS call_events (
    id                BIGSERIAL PRIMARY KEY,
    call_id           UUID REFERENCES calls(id) ON DELETE SET NULL,
    provider_call_sid TEXT,
    event_type        TEXT NOT NULL,
    payload           JSONB,
    idempotency_key   TEXT NOT NULL UNIQUE,
    received_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_call_events_provider_call_sid ON call_events(provider_call_sid);

-- ── templates ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS templates (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name             TEXT NOT NULL,
    use_case         TEXT NOT NULL,
    source_language  VARCHAR(2) NOT NULL DEFAULT 'en',
    variables        JSONB,
    script           JSONB,
    dtmf_map         JSONB,
    speech_enabled   BOOLEAN NOT NULL DEFAULT TRUE,
    voicemail_policy TEXT NOT NULL DEFAULT 'skip',
    is_preset        BOOLEAN NOT NULL DEFAULT FALSE,
    created_by       UUID,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── dnd_numbers ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dnd_numbers (
    phone_hash  VARCHAR(64) PRIMARY KEY,
    added_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── audit_log ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID,
    action      TEXT NOT NULL,
    object_type TEXT NOT NULL,
    object_id   TEXT NOT NULL,
    ip          TEXT,
    meta        JSONB,
    prev_hash   VARCHAR(64),
    row_hash    VARCHAR(64),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── execution_sessions ────────────────────────────────────────────────────
-- Shared across BROWSER_VOICE, TELEGRAM, TELEPHONY, SIMULATION channels.
-- is_simulation=TRUE records NEVER count in real telephony analytics.
CREATE TABLE IF NOT EXISTS execution_sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id         UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    execution_type      TEXT NOT NULL
                        CHECK (execution_type IN ('BROWSER_VOICE','TELEGRAM','TELEPHONY','SIMULATION')),
    language            VARCHAR(2) NOT NULL DEFAULT 'en',
    status              TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active','prompting','completed','abandoned','error')),
    is_simulation       BOOLEAN NOT NULL DEFAULT TRUE,
    prompt_text         TEXT,
    transcript          TEXT,
    intent              TEXT,
    confidence          NUMERIC(5,4),
    decision_method     TEXT,   -- 'rules'|'model'|'dtmf_keypad'|'keyword_fallback'|'llm'
    outcome             TEXT,
    error_meta          JSONB,
    telegram_chat_id    TEXT,   -- only for TELEGRAM sessions
    provider_session_id TEXT,   -- Exotel CallSid / Twilio CallSid / ElevenLabs conv_id
    responded_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_exec_sessions_campaign ON execution_sessions(campaign_id);
CREATE INDEX IF NOT EXISTS ix_exec_sessions_type ON execution_sessions(execution_type);
CREATE INDEX IF NOT EXISTS ix_exec_sessions_is_sim ON execution_sessions(is_simulation);

-- ── Row Level Security (enable but allow service role full access) ─────────
ALTER TABLE campaigns        ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts         ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE calls             ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_events       ENABLE ROW LEVEL SECURITY;
ALTER TABLE templates         ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS automatically in Supabase.
-- Add user-scoped policies here when multi-tenancy is required.

-- Done!
SELECT 'Schema applied successfully.' AS result;
