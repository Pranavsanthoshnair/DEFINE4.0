/**
 * demo-data.ts — Single source of truth for ALL demo mode data.
 *
 * This file is ONLY imported when isDemo === true.
 * Every page reads from here in demo mode; never hardcodes its own data.
 * In live mode, pages hit the real backend — zero data from this file.
 */

// ── Campaigns ────────────────────────────────────────────────────────────────

export const DEMO_CAMPAIGNS = [
  {
    id: "demo-1",
    name: "Annual Tech Summit 2026 — VIP Invites",
    status: "running",
    language: "en,hi,ta",
    contact_count: 2450,
    confirmed: 2063,
    rate: "84.2%",
    created_at: "2026-10-07T09:00:00Z",
  },
  {
    id: "demo-2",
    name: "Keynote RSVP Confirmation — Wave 1",
    status: "completed",
    language: "en,hi",
    contact_count: 1200,
    confirmed: 1102,
    rate: "91.8%",
    created_at: "2026-10-05T11:00:00Z",
  },
  {
    id: "demo-3",
    name: "Workshop Reminder — Day 2 Attendees",
    status: "scheduled",
    language: "en,mr",
    contact_count: 860,
    confirmed: 0,
    rate: "—",
    created_at: "2026-10-04T14:30:00Z",
  },
];

// ── Overview KPIs ─────────────────────────────────────────────────────────────

export const DEMO_OVERVIEW = {
  total_campaigns: 12,
  total_contacts: 8340,
  total_calls: 5210,
  calls_answered: 4387,
  calls_failed: 411,
  callbacks_pending: 47,
  eligible_for_retry: 133,
  confirmed_rate: "84.2%",
  campaigns: 12,
};

// ── Contacts ──────────────────────────────────────────────────────────────────

export const DEMO_CONTACTS = [
  { id: "c-1", name: "Arjun Sharma",   phone: "+91 99999 000 01", language: "Hindi",   segment: "VIP",      status: "confirmed",  campaign: "Annual Tech Summit 2026" },
  { id: "c-2", name: "Priya Nair",     phone: "+91 99999 000 02", language: "Tamil",   segment: "Speaker",  status: "confirmed",  campaign: "Annual Tech Summit 2026" },
  { id: "c-3", name: "Rohan Mehta",    phone: "+91 99999 000 03", language: "English", segment: "Sponsor",  status: "call_later", campaign: "Annual Tech Summit 2026" },
  { id: "c-4", name: "Ananya Iyer",    phone: "+91 99999 000 04", language: "Telugu",  segment: "General",  status: "declined",   campaign: "Keynote RSVP" },
  { id: "c-5", name: "Vikram Bose",    phone: "+91 99999 000 05", language: "English", segment: "VIP",      status: "confirmed",  campaign: "Keynote RSVP" },
  { id: "c-6", name: "Meera Pillai",   phone: "+91 99999 000 06", language: "Malayalam","segment": "Volunteer", status: "no_answer", campaign: "Workshop Reminder" },
  { id: "c-7", name: "Suresh Kumar",   phone: "+91 99999 000 07", language: "Kannada", segment: "General",  status: "pending",    campaign: "Workshop Reminder" },
  { id: "c-8", name: "Divya Reddy",    phone: "+91 99999 000 08", language: "Telugu",  segment: "Speaker",  status: "confirmed",  campaign: "Annual Tech Summit 2026" },
];

// ── Analytics ─────────────────────────────────────────────────────────────────

export const DEMO_ANALYTICS = {
  campaign_id: "demo-1",
  campaign_name: "Annual Tech Summit 2026 — VIP Invites",
  total: 2450,
  outcomes: {
    confirmed:  2063,
    declined:    189,
    call_later:   87,
    no_answer:    64,
    unclear:      47,
  },
  by_language: [
    { language: "Hindi",   confirmed: 980, total: 1100, rate: "89.1%" },
    { language: "Tamil",   confirmed: 620, total: 750,  rate: "82.7%" },
    { language: "English", confirmed: 463, total: 600,  rate: "77.2%" },
  ],
  by_day: [
    { date: "Oct 7",  calls: 820,  confirmed: 692 },
    { date: "Oct 8",  calls: 910,  confirmed: 768 },
    { date: "Oct 9",  calls: 720,  confirmed: 603 },
  ],
};

// ── Templates ─────────────────────────────────────────────────────────────────

export const DEMO_TEMPLATES = [
  {
    id: "t-1",
    name: "Event RSVP — Formal",
    language: "en,hi,ta,te",
    segments: ["greeting", "prompt", "confirm", "decline", "callback", "goodbye"],
    status: "approved",
    used_in: 3,
  },
  {
    id: "t-2",
    name: "Reminder — Day Before",
    language: "en,hi",
    segments: ["greeting", "prompt", "confirm", "goodbye"],
    status: "approved",
    used_in: 1,
  },
  {
    id: "t-3",
    name: "Workshop Invite — Casual",
    language: "en,mr,kn",
    segments: ["greeting", "prompt", "confirm", "decline", "goodbye"],
    status: "draft",
    used_in: 0,
  },
];

// ── Activity Feed ─────────────────────────────────────────────────────────────

export const DEMO_ACTIVITY = [
  { text: "Campaign 'Annual Tech Summit' launched",   time: "2h ago",  type: "launch" },
  { text: "1,102 contacts confirmed for Keynote RSVP", time: "4h ago", type: "success" },
  { text: "CSV imported — 2,450 contacts",             time: "6h ago", type: "import" },
  { text: "ElevenLabs audio pre-generated (6 clips)",  time: "6h ago", type: "audio" },
  { text: "Campaign 'Keynote RSVP' completed",         time: "Oct 8",  type: "complete" },
];

// ── Calls (browser simulator sessions) ───────────────────────────────────────

export const DEMO_CALLS = [
  { id: "s-1", contact: "Arjun Sharma",  intent: "confirm",    confidence: 0.97, method: "own-ai",  lang: "hi", transcript: "Haan, main zaroor aaonga" },
  { id: "s-2", contact: "Priya Nair",    intent: "confirm",    confidence: 0.93, method: "own-ai",  lang: "ta", transcript: "Aamam, naan varuven" },
  { id: "s-3", contact: "Rohan Mehta",   intent: "call_later", confidence: 0.88, method: "gemini",  lang: "en", transcript: "Can you call me tomorrow?" },
  { id: "s-4", contact: "Ananya Iyer",   intent: "decline",    confidence: 0.91, method: "own-ai",  lang: "te", transcript: "Raanu, naaku raadhu" },
];
