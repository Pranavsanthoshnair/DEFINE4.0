/**
 * MSW mock handlers — Member 4.
 *
 * Intercepts API requests when NEXT_PUBLIC_USE_MOCKS=true so the entire
 * frontend works without a running backend.
 *
 * Rules:
 *  - Every response shape exactly mirrors CONTRACTS.md §6.
 *  - Enum values are taken from CONTRACTS.md §3. Do not invent new ones.
 *  - Phone numbers are always masked — never put a real E.164 number here.
 *  - Fixture contacts use the mock suffix scheme from CONTRACTS.md §9.6:
 *    +9199999000NN, where NN drives mock call behaviour deterministically.
 */

import { http, HttpResponse, delay } from "msw";

// ── Shared outcome shape ──────────────────────────────────────────────────────

interface OutcomeCounts {
  confirmed: number; declined: number; reschedule: number; call_later: number;
  unclear: number; no_answer: number; busy: number; voicemail: number;
  failed: number; no_input: number; opted_out: number; pending: number;
}

function zeroOutcomes(): OutcomeCounts {
  return {
    confirmed: 0, declined: 0, reschedule: 0, call_later: 0,
    unclear: 0, no_answer: 0, busy: 0, voicemail: 0,
    failed: 0, no_input: 0, opted_out: 0, pending: 0,
  };
}

// ── In-memory campaign store ──────────────────────────────────────────────────

/** Typed shape matching CONTRACTS.md §4 campaigns table (frontend-relevant fields). */
interface MockCampaign {
  id: string;
  name: string;
  template_id: string;
  status: string;
  event_details: Record<string, string>;
  variable_overrides: Record<string, Record<string, string>>;
  languages: string[];
  caller_id: string | null;
  calling_window_start: string;
  calling_window_end: string;
  timezone: string;
  max_attempts: number;
  max_concurrent_calls: number;
  created_by: string;
  created_at: string;
  launched_at: string | null;
  completed_at: string | null;
}

const DEMO_CAMPAIGNS: Record<string, MockCampaign> = {
  "camp-001": {
    id: "camp-001",
    name: "AI & Society Seminar 2026",
    template_id: "tpl-seminar",
    status: "running",
    event_details: { event_name: "AI & Society Seminar", date: "18 October", venue: "Main Auditorium" },
    variable_overrides: {},
    languages: ["en", "hi", "ml", "ta"],
    caller_id: null,
    calling_window_start: "09:00",
    calling_window_end: "21:00",
    timezone: "Asia/Kolkata",
    max_attempts: 3,
    max_concurrent_calls: 3,
    created_by: "user-admin",
    created_at: "2026-10-09T05:00:00Z",
    launched_at: "2026-10-09T05:10:00Z",
    completed_at: null,
  },
  "camp-002": {
    id: "camp-002",
    name: "Workshop Reminder — Clinic",
    template_id: "tpl-clinic",
    status: "completed",
    event_details: { event_name: "Health Workshop", date: "5 October", venue: "City Clinic" },
    variable_overrides: {},
    languages: ["en", "hi"],
    caller_id: null,
    calling_window_start: "09:00",
    calling_window_end: "21:00",
    timezone: "Asia/Kolkata",
    max_attempts: 3,
    max_concurrent_calls: 3,
    created_by: "user-admin",
    created_at: "2026-10-04T06:00:00Z",
    launched_at: "2026-10-04T06:05:00Z",
    completed_at: "2026-10-04T14:00:00Z",
  },
  "camp-003": {
    id: "camp-003",
    name: "School Fee Reminder",
    template_id: "tpl-school",
    status: "draft",
    event_details: { event_name: "Fee Payment", date: "20 October", venue: "School Office" },
    variable_overrides: {},
    languages: ["en", "ta"],
    caller_id: null,
    calling_window_start: "09:00",
    calling_window_end: "21:00",
    timezone: "Asia/Kolkata",
    max_attempts: 3,
    max_concurrent_calls: 3,
    created_by: "user-admin",
    created_at: "2026-10-09T10:00:00Z",
    launched_at: null,
    completed_at: null,
  },
};

// ── Helpers ───────────────────────────────────────────────────────────────────

const MOCK_DELAY_MS = 300;

/** Prefix every path with the configured API base URL (empty string in dev). */
const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
function u(path: string): string {
  return `${BASE}${path}`;
}

function runningSummary(id: string) {
  return {
    campaign_id: id,
    status: "running",
    total_contacts: 200,
    attempted: 140,
    pending: 60,
    exhausted: 12,
    outcomes: {
      confirmed: 70, declined: 20, reschedule: 5, call_later: 3,
      unclear: 6,  no_answer: 18, busy: 4,  voicemail: 9,
      failed: 1,   no_input: 4,   opted_out: 0, pending: 60,
    } satisfies OutcomeCounts,
    answer_rate: 0.71,
    response_rate: 0.63,
    updated_at: new Date().toISOString(),
  };
}

function completedSummary(id: string, completedAt: string) {
  return {
    campaign_id: id,
    status: "completed",
    total_contacts: 150,
    attempted: 150,
    pending: 0,
    exhausted: 8,
    outcomes: {
      confirmed: 95, declined: 18, reschedule: 7, call_later: 2,
      unclear: 3,  no_answer: 10, busy: 3,  voicemail: 7,
      failed: 0,   no_input: 5,   opted_out: 0, pending: 0,
    } satisfies OutcomeCounts,
    answer_rate: 0.87,
    response_rate: 0.82,
    updated_at: completedAt,
  };
}

// ── Handlers ──────────────────────────────────────────────────────────────────

export const handlers = [

  // ── Auth ────────────────────────────────────────────────────────────────────

  /** POST /api/auth/login — accepts any credentials in mock mode. */
  http.post(u("/api/auth/login"), async () => {
    await delay(MOCK_DELAY_MS);
    return HttpResponse.json({
      access_token: "mock-jwt-for-development-only",
      token_type: "bearer",
      user: { id: "user-admin", email: "demo@veylo.dev", role: "admin" },
    });
  }),

  /** GET /api/auth/me */
  http.get(u("/api/auth/me"), async () => {
    await delay(MOCK_DELAY_MS);
    return HttpResponse.json({ id: "user-admin", email: "demo@veylo.dev", role: "admin" });
  }),

  // ── Templates ───────────────────────────────────────────────────────────────

  /**
   * GET /api/templates — the four contract presets (CONTRACTS.md §4, §5).
   * Script keys match the segment_key table in §5 exactly.
   */
  http.get(u("/api/templates"), async () => {
    await delay(MOCK_DELAY_MS);
    return HttpResponse.json([
      {
        id: "tpl-seminar",
        name: "Seminar Invitation",
        use_case: "seminar",
        source_language: "en",
        is_preset: true,
        speech_enabled: true,
        voicemail_policy: "leave_message",
        dtmf_map: { "1": "confirm", "2": "decline", "3": "reschedule", "9": "stop_calling" },
        variables: [
          { key: "event_name", label: "Event name", required: true },
          { key: "date",       label: "Date",        required: true },
          { key: "venue",      label: "Venue",       required: true },
        ],
        script: {
          greeting:       "Hello. This is a call from {org_name} about {event_name}.",
          prompt:         "You are invited to {event_name} on {date} at {venue}. Press 1 to confirm, 2 to decline, or 3 to reschedule.",
          reprompt:       "Sorry, I did not catch that. Press 1 to confirm, 2 to decline, or 3 to reschedule.",
          ack_confirm:    "Thank you. Your attendance is confirmed.",
          ack_decline:    "Thank you. We have noted that you cannot attend.",
          ack_reschedule: "Thank you. We will contact you about another time.",
          ack_call_later: "Thank you. We will call you again later.",
          ack_stop:       "Understood. We will not call you again.",
          ack_unclear:    "Sorry, we could not record your response.",
          voicemail:      "Hello, this is {org_name} inviting you to {event_name} on {date}. Please call us back.",
          goodbye:        "Thank you. Goodbye.",
        },
        created_by: "user-admin",
        created_at: "2026-10-01T00:00:00Z",
      },
      {
        id: "tpl-clinic",
        name: "Clinic Appointment Reminder",
        use_case: "clinic",
        source_language: "en",
        is_preset: true,
        speech_enabled: true,
        voicemail_policy: "leave_message",
        dtmf_map: { "1": "confirm", "3": "reschedule", "9": "stop_calling" },
        variables: [
          { key: "event_name", label: "Appointment type", required: true },
          { key: "date",       label: "Date",             required: true },
          { key: "venue",      label: "Clinic name",      required: true },
        ],
        script: {
          greeting:       "Hello. This is a reminder from {org_name} about your {event_name}.",
          prompt:         "Your appointment is on {date} at {venue}. Press 1 to confirm or 3 to reschedule.",
          reprompt:       "Press 1 to confirm or 3 to reschedule.",
          ack_confirm:    "Thank you. Your appointment is confirmed.",
          ack_decline:    "Understood.",
          ack_reschedule: "We will contact you to reschedule.",
          ack_call_later: "We will call you again later.",
          ack_stop:       "Understood. We will not call you again.",
          ack_unclear:    "Sorry, we could not record your response.",
          voicemail:      "Hello, this is {org_name}. Please call us to confirm your appointment.",
          goodbye:        "Goodbye.",
        },
        created_by: "user-admin",
        created_at: "2026-10-01T00:00:00Z",
      },
      {
        id: "tpl-school",
        name: "School Parent Notice",
        use_case: "school",
        source_language: "en",
        is_preset: true,
        speech_enabled: true,
        voicemail_policy: "leave_message",
        dtmf_map: { "1": "confirm", "5": "call_later", "9": "stop_calling" },
        variables: [
          { key: "event_name", label: "Notice subject", required: true },
          { key: "date",       label: "Date",           required: true },
          { key: "venue",      label: "School name",    required: true },
        ],
        script: {
          greeting:       "Hello. This is a message from {venue} for parents.",
          prompt:         "Regarding {event_name} on {date}. Press 1 to acknowledge or 5 to receive a call later.",
          reprompt:       "Press 1 to acknowledge.",
          ack_confirm:    "Thank you. We have recorded your acknowledgment.",
          ack_decline:    "Understood.",
          ack_reschedule: "We will contact you about another time.",
          ack_call_later: "We will call you again later.",
          ack_stop:       "Understood. We will not call you again.",
          ack_unclear:    "Sorry, we could not record your response.",
          voicemail:      "Hello, this is {venue}. Please call us regarding {event_name}.",
          goodbye:        "Goodbye.",
        },
        created_by: "user-admin",
        created_at: "2026-10-01T00:00:00Z",
      },
      {
        id: "tpl-payment",
        name: "Payment Reminder",
        use_case: "payment",
        source_language: "en",
        is_preset: true,
        speech_enabled: false,          // DTMF only — CONTRACTS.md locked decisions
        voicemail_policy: "skip_and_retry", // no voicemail message for payment
        dtmf_map: { "1": "confirm", "2": "call_later", "9": "stop_calling" },
        variables: [
          { key: "event_name", label: "Payment subject", required: true },
          { key: "date",       label: "Due date",        required: true },
          { key: "venue",      label: "Office name",     required: true },
        ],
        script: {
          greeting:       "Hello. This is a payment reminder from {org_name}.",
          prompt:         "Your payment for {event_name} is due on {date}. Press 1 if you will pay, or 2 to request more time.",
          reprompt:       "Press 1 to confirm payment or 2 for more time.",
          ack_confirm:    "Thank you. We will note that you will make the payment.",
          ack_decline:    "Understood.",
          ack_reschedule: "We will contact you again.",
          ack_call_later: "We will call you again later.",
          ack_stop:       "Understood. We will not call you again.",
          ack_unclear:    "Sorry, we could not record your response.",
          voicemail:      "",
          goodbye:        "Thank you. Goodbye.",
        },
        created_by: "user-admin",
        created_at: "2026-10-01T00:00:00Z",
      },
    ]);
  }),

  // ── Campaigns ───────────────────────────────────────────────────────────────

  /** POST /api/campaigns — create and store in the in-memory map. */
  http.post(u("/api/campaigns"), async ({ request }) => {
    await delay(MOCK_DELAY_MS);
    const body = await request.json() as Record<string, unknown>;
    const id = `camp-${Date.now()}`;
    const campaign: MockCampaign = {
      id,
      name:                  String(body.name ?? "New Campaign"),
      template_id:           String(body.template_id ?? ""),
      status:                "draft",
      event_details:         (body.event_details as Record<string, string>) ?? {},
      variable_overrides:    (body.variable_overrides as Record<string, Record<string, string>>) ?? {},
      languages:             (body.languages as string[]) ?? ["en"],
      caller_id:             null,
      calling_window_start:  String(body.calling_window_start ?? "09:00"),
      calling_window_end:    String(body.calling_window_end ?? "21:00"),
      timezone:              "Asia/Kolkata",
      max_attempts:          Number(body.max_attempts ?? 3),
      max_concurrent_calls:  Number(body.max_concurrent_calls ?? 3),
      created_by:            "user-admin",
      created_at:            new Date().toISOString(),
      launched_at:           null,
      completed_at:          null,
    };
    DEMO_CAMPAIGNS[id] = campaign;
    return HttpResponse.json(campaign, { status: 201 });
  }),

  /** GET /api/campaigns — paginated list. */
  http.get(u("/api/campaigns"), async ({ request }) => {
    await delay(MOCK_DELAY_MS);
    const qs   = new URL(request.url).searchParams;
    const page = Number(qs.get("page") ?? 1);
    const ps   = Number(qs.get("page_size") ?? 25);
    const all  = Object.values(DEMO_CAMPAIGNS).sort(
      (a: MockCampaign, b: MockCampaign) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
    const start = (page - 1) * ps;
    return HttpResponse.json({ items: all.slice(start, start + ps), page, page_size: ps, total: all.length });
  }),

  /** GET /api/campaigns/:id — single campaign with readiness. */
  http.get(u("/api/campaigns/:id"), async ({ params }) => {
    await delay(MOCK_DELAY_MS);
    const id = params.id as string;
    const campaign = DEMO_CAMPAIGNS[id];
    if (!campaign) {
      return HttpResponse.json(
        { error: { code: "not_found", message: "Campaign not found", details: {} } },
        { status: 404 }
      );
    }
    const launched = campaign.status === "ready" || campaign.status === "running" || campaign.status === "completed";
    const readiness = {
      has_contacts: campaign.status !== "draft",
      languages: Object.fromEntries(
        campaign.languages.map((lang: string) => [
          lang,
          { translation: launched ? "approved" : "draft", audio: launched ? "ready" : "missing" },
        ])
      ),
      can_launch: campaign.status === "ready",
      blockers: campaign.status === "needs_review"
        ? campaign.languages.map((l: string) => `translation_not_approved:${l}`)
        : [],
    };
    return HttpResponse.json({ ...campaign, readiness });
  }),

  /** POST /api/campaigns/:id/prepare — advances to needs_review. */
  http.post(u("/api/campaigns/:id/prepare"), async ({ params }) => {
    await delay(MOCK_DELAY_MS * 2);
    const id = params.id as string;
    const campaign = DEMO_CAMPAIGNS[id];
    if (!campaign) {
      return HttpResponse.json(
        { error: { code: "not_found", message: "Campaign not found", details: {} } },
        { status: 404 }
      );
    }
    campaign.status = "needs_review";
    return HttpResponse.json({ status: "preparing" }, { status: 202 });
  }),

  /** POST /api/campaigns/:id/launch — transitions to running. */
  http.post(u("/api/campaigns/:id/launch"), async ({ params }) => {
    await delay(MOCK_DELAY_MS);
    const id = params.id as string;
    const campaign = DEMO_CAMPAIGNS[id];
    if (!campaign) {
      return HttpResponse.json(
        { error: { code: "not_found", message: "Campaign not found", details: {} } },
        { status: 404 }
      );
    }
    campaign.status = "running";
    campaign.launched_at = new Date().toISOString();
    return HttpResponse.json({ status: "running" });
  }),

  /** GET /api/campaigns/:id/summary — realistic numbers per status. */
  http.get(u("/api/campaigns/:id/summary"), async ({ params }) => {
    await delay(MOCK_DELAY_MS);
    const id = params.id as string;
    const campaign = DEMO_CAMPAIGNS[id];
    if (!campaign) {
      return HttpResponse.json(
        { error: { code: "not_found", message: "Campaign not found", details: {} } },
        { status: 404 }
      );
    }
    if (campaign.status === "running")   return HttpResponse.json(runningSummary(id));
    if (campaign.status === "completed") return HttpResponse.json(completedSummary(id, campaign.completed_at ?? new Date().toISOString()));
    return HttpResponse.json({
      campaign_id: id, status: campaign.status,
      total_contacts: 0, attempted: 0, pending: 0, exhausted: 0,
      outcomes: zeroOutcomes(), answer_rate: 0, response_rate: 0,
      updated_at: new Date().toISOString(),
    });
  }),

  // ── Overview ─────────────────────────────────────────────────────────────────

  /** GET /api/overview — cross-campaign totals for the home page. */
  http.get(u("/api/overview"), async () => {
    await delay(MOCK_DELAY_MS);
    const all = Object.values(DEMO_CAMPAIGNS) as MockCampaign[];
    return HttpResponse.json({
      total_campaigns:  all.length,
      running:          all.filter((c: MockCampaign) => c.status === "running").length,
      completed:        all.filter((c: MockCampaign) => c.status === "completed").length,
      total_contacts:   350,
      total_attempted:  290,
      total_confirmed:  165,
      answer_rate:      0.79,
      response_rate:    0.71,
      recent_campaigns: all
        .sort((a: MockCampaign, b: MockCampaign) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )
        .slice(0, 5)
        .map((c: MockCampaign) => ({ id: c.id, name: c.name, status: c.status, created_at: c.created_at })),
    });
  }),

  // ── Health ────────────────────────────────────────────────────────────────────

  http.get(u("/healthz"), async () => {
    return HttpResponse.json({ status: "ok" });
  }),
];
