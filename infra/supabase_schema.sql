-- Veylo — Supabase SQL Schema (with Row Level Security enabled on all tables)
-- Run this in: Supabase Dashboard → SQL Editor → New Query
-- Project: mmhsjabzjlfpagdhxrcs

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── 1. users ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'organiser' CHECK (role IN ('admin', 'organiser')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- ── 2. campaigns ───────────────────────────────────────────────────────────
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
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;

-- ── 3. contacts ───────────────────────────────────────────────────────────
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
    telegram_chat_id TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_contacts_phone_hash ON contacts(phone_hash);
CREATE INDEX IF NOT EXISTS ix_contacts_telegram_chat_id ON contacts(telegram_chat_id);
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;

-- ── 4. campaign_contacts ──────────────────────────────────────────────────
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
ALTER TABLE campaign_contacts ENABLE ROW LEVEL SECURITY;

-- ── 5. calls ──────────────────────────────────────────────────────────────
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
ALTER TABLE calls ENABLE ROW LEVEL SECURITY;

-- ── 6. call_events ─────────────────────────────────────────────────────────
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
ALTER TABLE call_events ENABLE ROW LEVEL SECURITY;

-- ── 7. templates ──────────────────────────────────────────────────────────
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

ALTER TABLE templates ENABLE ROW LEVEL SECURITY;

-- ── 8. dnd_numbers ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dnd_numbers (
    phone_hash  VARCHAR(64) PRIMARY KEY,
    added_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE dnd_numbers ENABLE ROW LEVEL SECURITY;

-- ── 9. audit_log ──────────────────────────────────────────────────────────
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

ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- ── 10. execution_sessions ─────────────────────────────────────────────────
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
    decision_method     TEXT,
    outcome             TEXT,
    error_meta          JSONB,
    telegram_chat_id    TEXT,
    provider_session_id TEXT,
    responded_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_exec_sessions_campaign ON execution_sessions(campaign_id);
CREATE INDEX IF NOT EXISTS ix_exec_sessions_type ON execution_sessions(execution_type);
CREATE INDEX IF NOT EXISTS ix_exec_sessions_is_sim ON execution_sessions(is_simulation);
ALTER TABLE execution_sessions ENABLE ROW LEVEL SECURITY;

-- ── Allow authenticated/service role full access policies ─────────────────
DO $$
BEGIN
    -- users policy
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'users' AND policyname = 'service_role_all_users') THEN
        CREATE POLICY service_role_all_users ON users FOR ALL TO authenticated, service_role USING (true) WITH CHECK (true);
    END IF;
    -- campaigns policy
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'campaigns' AND policyname = 'service_role_all_campaigns') THEN
        CREATE POLICY service_role_all_campaigns ON campaigns FOR ALL TO authenticated, service_role USING (true) WITH CHECK (true);
    END IF;
    -- contacts policy
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'contacts' AND policyname = 'service_role_all_contacts') THEN
        CREATE POLICY service_role_all_contacts ON contacts FOR ALL TO authenticated, service_role USING (true) WITH CHECK (true);
    END IF;
    -- campaign_contacts policy
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'campaign_contacts' AND policyname = 'service_role_all_cc') THEN
        CREATE POLICY service_role_all_cc ON campaign_contacts FOR ALL TO authenticated, service_role USING (true) WITH CHECK (true);
    END IF;
    -- calls policy
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'calls' AND policyname = 'service_role_all_calls') THEN
        CREATE POLICY service_role_all_calls ON calls FOR ALL TO authenticated, service_role USING (true) WITH CHECK (true);
    END IF;
    -- call_events policy
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'call_events' AND policyname = 'service_role_all_events') THEN
        CREATE POLICY service_role_all_events ON call_events FOR ALL TO authenticated, service_role USING (true) WITH CHECK (true);
    END IF;
    -- templates policy
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'templates' AND policyname = 'service_role_all_templates') THEN
        CREATE POLICY service_role_all_templates ON templates FOR ALL TO authenticated, service_role USING (true) WITH CHECK (true);
    END IF;
    -- dnd_numbers policy
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'dnd_numbers' AND policyname = 'service_role_all_dnd') THEN
        CREATE POLICY service_role_all_dnd ON dnd_numbers FOR ALL TO authenticated, service_role USING (true) WITH CHECK (true);
    END IF;
    -- audit_log policy
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'audit_log' AND policyname = 'service_role_all_audit') THEN
        CREATE POLICY service_role_all_audit ON audit_log FOR ALL TO authenticated, service_role USING (true) WITH CHECK (true);
    END IF;
    -- execution_sessions policy
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'execution_sessions' AND policyname = 'service_role_all_exec') THEN
        CREATE POLICY service_role_all_exec ON execution_sessions FOR ALL TO authenticated, service_role USING (true) WITH CHECK (true);
    END IF;
END $$;

-- Done!
SELECT 'Schema applied successfully with RLS enabled on all tables.' AS result;
