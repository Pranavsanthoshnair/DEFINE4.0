/**
 * Centralised API client.
 * All backend calls go through here — no scattered fetch() calls in components.
 *
 * Auth: reads the Supabase session and attaches Authorization: Bearer <token>
 * to every request. Falls back silently when no session exists (public routes).
 */

import { createClient } from "@supabase/supabase-js";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Supabase client for reading the current session token only.
// Uses public keys — safe for browser.
const _supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "",
);

async function _getAuthHeader(): Promise<Record<string, string>> {
  try {
    const { data } = await _supabase.auth.getSession();
    const token = data.session?.access_token;
    if (token) return { Authorization: `Bearer ${token}` };
  } catch {
    // Not authenticated — public route, continue without header
  }
  return {};
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
};

async function request<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = "GET", body, headers = {} } = options;

  const authHeader = await _getAuthHeader();

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...authHeader,
      ...headers,   // caller-provided headers override auth if needed
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });

  if (!res.ok) {
    const errorBody = await res.text().catch(() => "Unknown error");
    throw new Error(`API error ${res.status}: ${errorBody}`);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}


// ── Health ──────────────────────────────────────────────────────────────────

export const healthApi = {
  check: () => request<{ status: string; version: string }>("/health"),
};

// ── Campaigns ───────────────────────────────────────────────────────────────

export const campaignsApi = {
  list: () => request<Campaign[]>("/api/v1/campaigns/"),
  get: (id: string) => request<Campaign>(`/api/v1/campaigns/${id}`),
  create: (payload: CampaignCreate) =>
    request<Campaign>("/api/v1/campaigns/", { method: "POST", body: payload }),
  delete: (id: string) =>
    request<void>(`/api/v1/campaigns/${id}`, { method: "DELETE" }),
};

// ── Contacts ────────────────────────────────────────────────────────────────

export const contactsApi = {
  list: () => request<Contact[]>("/api/v1/contacts/"),
};

// ── Analytics ───────────────────────────────────────────────────────────────

export const analyticsApi = {
  getCampaignStats: (campaignId: string) =>
    request<CampaignStats>(`/api/v1/analytics/${campaignId}`),
};

// ── Local type aliases (duplicated from types/ for colocation) ───────────────

import type { Campaign, CampaignCreate, Contact, CampaignStats } from "@/types";
