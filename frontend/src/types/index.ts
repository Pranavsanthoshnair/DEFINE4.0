/**
 * Shared TypeScript types for Veylo — Member 4 frontend.
 *
 * These types are derived directly from CONTRACTS.md (sections 3, 4, 6).
 * Field names, enum values, and response shapes must stay in sync with that document.
 * Do not invent fields or change enum strings without a contract-change PR.
 */

// ─────────────────────────────────────────────────────────────────────────────
// Enums — exact string values from CONTRACTS.md §3
// ─────────────────────────────────────────────────────────────────────────────

/** Status values for a campaign. CONTRACTS.md §3 */
export type CampaignStatus =
  | "draft"
  | "preparing"
  | "needs_review"
  | "ready"
  | "running"
  | "paused"
  | "completed"
  | "cancelled";

/** All possible per-contact outcomes. CONTRACTS.md §3 */
export type Outcome =
  | "pending"
  | "confirmed"
  | "declined"
  | "reschedule"
  | "call_later"
  | "unclear"
  | "no_answer"
  | "busy"
  | "voicemail"
  | "failed"
  | "no_input"
  | "opted_out";

/** State of a single campaign_contact row. CONTRACTS.md §3 */
export type ContactState =
  | "pending"
  | "in_call"
  | "waiting_retry"
  | "done"
  | "exhausted"
  | "skipped";

/** Status values for an individual call. CONTRACTS.md §3 */
export type CallStatus =
  | "initiated"
  | "ringing"
  | "in_progress"
  | "completed"
  | "failed"
  | "busy"
  | "no_answer"
  | "canceled";

/** Use-case categories for templates. CONTRACTS.md §3 */
export type UseCase = "seminar" | "clinic" | "school" | "payment" | "custom";

/** Translation approval status. CONTRACTS.md §3 */
export type TranslationStatus = "draft" | "approved";

/** Voicemail handling policy. CONTRACTS.md §3 */
export type VoicemailPolicy = "leave_message" | "skip_and_retry";

/** User roles. CONTRACTS.md §3 */
export type UserRole = "admin" | "organiser";

// ─────────────────────────────────────────────────────────────────────────────
// Auth — CONTRACTS.md §6 Auth
// ─────────────────────────────────────────────────────────────────────────────

export interface AuthUser {
  id: string;
  email: string;
  role: UserRole;
}

/** Response from POST /api/auth/login */
export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
}

// ─────────────────────────────────────────────────────────────────────────────
// Templates — CONTRACTS.md §4 / §6 Templates
// ─────────────────────────────────────────────────────────────────────────────

/** One variable descriptor inside a template's `variables` JSONB field. */
export interface TemplateVariable {
  key: string;
  label: string;
  required: boolean;
}

/** All segment keys for a script (CONTRACTS.md §5). Values are strings with {placeholder} tokens. */
export type ScriptSegments = Record<string, string>;

export interface Template {
  id: string;
  name: string;
  use_case: UseCase;
  source_language: string;   // ISO 639-1, e.g. "en"
  variables: TemplateVariable[];
  script: ScriptSegments;    // source-language script
  dtmf_map: Record<string, string>; // e.g. {"1":"confirm","2":"decline"}
  speech_enabled: boolean;
  voicemail_policy: VoicemailPolicy;
  is_preset: boolean;
  created_by: string;        // user UUID
  created_at: string;        // ISO 8601 UTC
}

/** One translation per language for a template. */
export interface TemplateTranslation {
  id: string;
  template_id: string;
  language: string;
  segments: ScriptSegments;
  status: TranslationStatus;
  source: "ai" | "manual";
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Campaigns — CONTRACTS.md §4 / §6 Campaigns
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Readiness of a campaign before launch.
 * Returned inside GET /api/campaigns/{id}.
 */
export interface CampaignReadiness {
  has_contacts: boolean;
  /** Per-language readiness: { "hi": { translation: "approved", audio: "ready" } } */
  languages: Record<string, { translation: TranslationStatus; audio: "ready" | "missing" }>;
  can_launch: boolean;
  /** e.g. ["translation_not_approved:ml"] */
  blockers: string[];
}

export interface Campaign {
  id: string;
  name: string;
  template_id: string;
  status: CampaignStatus;
  event_details: Record<string, string>;   // values for template variables
  variable_overrides: Record<string, Record<string, string>>; // per-language overrides
  languages: string[];
  caller_id: string | null;
  calling_window_start: string;  // "09:00"
  calling_window_end: string;    // "21:00"
  timezone: string;
  max_attempts: number;
  max_concurrent_calls: number;
  created_by: string;
  created_at: string;
  launched_at: string | null;
  completed_at: string | null;
  readiness?: CampaignReadiness; // present on GET single campaign
}

/** Body for POST /api/campaigns */
export interface CampaignCreate {
  name: string;
  template_id: string;
  event_details: Record<string, string>;
  variable_overrides?: Record<string, Record<string, string>>;
  languages: string[];
  caller_id?: string;
  calling_window_start?: string;
  calling_window_end?: string;
  max_attempts?: number;
  max_concurrent_calls?: number;
}

/**
 * All outcome keys present in the summary response.
 * Every key is always present, zero-filled. CONTRACTS.md §6.
 */
export interface OutcomeCounts {
  confirmed: number;
  declined: number;
  reschedule: number;
  call_later: number;
  unclear: number;
  no_answer: number;
  busy: number;
  voicemail: number;
  failed: number;
  no_input: number;
  opted_out: number;
  pending: number;
}

/** Response from GET /api/campaigns/{id}/summary */
export interface CampaignSummary {
  campaign_id: string;
  status: CampaignStatus;
  total_contacts: number;
  attempted: number;
  pending: number;
  exhausted: number;
  outcomes: OutcomeCounts;
  /** answered calls / attempted contacts */
  answer_rate: number;
  /** contacts with intent captured / answered contacts */
  response_rate: number;
  updated_at: string;
}

/** One row in the breakdown response. */
export interface BreakdownRow {
  key: string;       // language code or segment name
  total: number;
  outcomes: OutcomeCounts;
}

/** Response from GET /api/campaigns/{id}/breakdown?by=language|segment */
export interface BreakdownResponse {
  by: "language" | "segment";
  rows: BreakdownRow[];
}

// ─────────────────────────────────────────────────────────────────────────────
// Contacts — CONTRACTS.md §4 / §6 Contacts
// ─────────────────────────────────────────────────────────────────────────────

/**
 * A contact row as returned in the campaign contacts list.
 * Phone is always masked ("+91XXXXXX3210") — never store or log the unmasked number.
 */
export interface CampaignContact {
  id: string;
  contact_id: string | null;   // null if the contact was erased (right to erasure)
  phone_last4: string;         // 4 digits only, for display
  phone_masked: string;        // e.g. "+91XXXXXX3210"
  language: string;
  segment: string | null;
  state: ContactState;
  attempts: number;
  last_outcome: Outcome | null;
  final_outcome: Outcome | null;
  next_attempt_at: string | null;
  last_call_at: string | null;
}

/** CSV import result from POST /api/campaigns/{id}/contacts/import */
export interface ImportResult {
  imported: number;
  skipped: number;
  errors: Array<{ row: number; reason: string }>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Overview — CONTRACTS.md §6 GET /api/overview
// ─────────────────────────────────────────────────────────────────────────────

/** Response from GET /api/overview — totals across all campaigns for the home page. */
export interface Overview {
  total_campaigns: number;
  running: number;
  completed: number;
  total_contacts: number;
  total_attempted: number;
  total_confirmed: number;
  answer_rate: number;
  response_rate: number;
  /** Most recent campaigns, newest first */
  recent_campaigns: Array<Pick<Campaign, "id" | "name" | "status" | "created_at">>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Pagination — CONTRACTS.md §2
// ─────────────────────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Error format — CONTRACTS.md §2
// ─────────────────────────────────────────────────────────────────────────────

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
}
