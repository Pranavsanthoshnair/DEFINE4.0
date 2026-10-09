/**
 * Shared TypeScript types for Veylo.
 * Keep in sync with backend Pydantic schemas.
 */

// ── Campaign ─────────────────────────────────────────────────────────────────

export type CampaignStatus =
  | "draft"
  | "active"
  | "paused"
  | "completed"
  | "archived";

export interface Campaign {
  id: string;
  name: string;
  description?: string;
  language: string;
  status: CampaignStatus;
  created_at: string;
}

export interface CampaignCreate {
  name: string;
  description?: string;
  language: string;
  brief?: string;
}

// ── Contact ──────────────────────────────────────────────────────────────────

export interface Contact {
  id: string;
  name?: string;
  phone: string;
  language?: string;
}

// ── CampaignRecipient ────────────────────────────────────────────────────────

export type RecipientOutcome =
  | "pending"
  | "answered"
  | "no_answer"
  | "voicemail"
  | "failed"
  | "do_not_call";

export interface CampaignRecipient {
  id: string;
  campaign_id: string;
  contact_id: string;
  outcome: RecipientOutcome;
  attempts: number;
}

// ── CallAttempt ──────────────────────────────────────────────────────────────

export type CallStatus =
  | "initiated"
  | "ringing"
  | "in-progress"
  | "completed"
  | "failed"
  | "busy"
  | "no-answer";

export interface CallAttempt {
  id: string;
  recipient_id: string;
  exotel_call_sid?: string;
  status: CallStatus;
  started_at?: string;
  ended_at?: string;
  duration_seconds?: number;
}

// ── Analytics ────────────────────────────────────────────────────────────────

export interface CampaignStats {
  campaign_id: string;
  total_recipients: number;
  calls_attempted: number;
  calls_answered: number;
  calls_failed: number;
  completion_rate: number;
}
