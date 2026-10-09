/**
 * Centralised API client.
 * All backend calls go through here — no scattered fetch() calls in components.
 */

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...headers,
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
