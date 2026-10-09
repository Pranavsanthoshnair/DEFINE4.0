/**
 * Centralised API client for Veylo - Member 4.
 *
 * CONTRACTS.md rules:
 *  - Base URL from NEXT_PUBLIC_API_BASE_URL (s11)
 *  - All paths /api/... with NO /v1/ prefix (s2, s6)
 *  - Authorization: Bearer <JWT> on every authenticated request (s2)
 *  - Error body: { "error": { "code", "message", "details" } } (s2)
 *  - 401 redirects to /login
 *  - Never log phone numbers, names, or transcripts (s2)
 */

import type {
  LoginResponse,
  AuthUser,
  Campaign,
  CampaignCreate,
  CampaignSummary,
  BreakdownResponse,
  CampaignContact,
  ImportResult,
  PaginatedResponse,
  Overview,
  Template,
  TemplateTranslation,
  ApiErrorBody,
} from "@/types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8100";

// Token helpers (sessionStorage - fallback approach per member-4 doc s3)

const TOKEN_KEY = "veylo_token";

export function setToken(token: string): void {
  if (typeof window !== "undefined") sessionStorage.setItem(TOKEN_KEY, token);
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(TOKEN_KEY);
}

export function clearToken(): void {
  if (typeof window !== "undefined") sessionStorage.removeItem(TOKEN_KEY);
}

// Typed error class

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details: Record<string, unknown> = {}
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// Core request helper

type RequestOptions = {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  multipart?: boolean;
  public?: boolean;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {}, multipart = false } = options;
  const token = getToken();
  const reqHeaders: Record<string, string> = { ...headers };

  if (!options.public && token) reqHeaders["Authorization"] = `Bearer ${token}`;
  if (!multipart && body !== undefined) reqHeaders["Content-Type"] = "application/json";

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: reqHeaders,
    ...(body !== undefined ? { body: multipart ? (body as FormData) : JSON.stringify(body) } : {}),
  });

  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new ApiError(401, "unauthorized", "Session expired. Please log in again.");
  }

  if (res.status === 204) return undefined as T;

  let json: unknown;
  try {
    json = await res.json();
  } catch {
    throw new ApiError(res.status, "parse_error", `HTTP ${res.status}: non-JSON response`);
  }

  if (!res.ok) {
    const errBody = json as Partial<ApiErrorBody>;
    const err = errBody?.error;
    throw new ApiError(
      res.status,
      err?.code ?? "unknown_error",
      err?.message ?? `HTTP ${res.status}`,
      err?.details ?? {}
    );
  }

  return json as T;
}

// Auth

export const authApi = {
  login: async (email: string, password: string): Promise<LoginResponse> => {
    const res = await request<LoginResponse>("/api/auth/login", {
      method: "POST",
      body: { email, password },
      public: true,
    });
    setToken(res.access_token);
    return res;
  },
  me: () => request<AuthUser>("/api/auth/me"),
  logout: () => clearToken(),
};

// Templates

export const templatesApi = {
  list: () => request<Template[]>("/api/templates"),
  get: (id: string) => request<Template>(`/api/templates/${id}`),
  listTranslations: (id: string) =>
    request<TemplateTranslation[]>(`/api/templates/${id}/translations`),
  saveTranslation: (id: string, lang: string, segments: Record<string, string>) =>
    request<TemplateTranslation>(`/api/templates/${id}/translations/${lang}`, {
      method: "PUT",
      body: { segments },
    }),
  approveTranslation: (id: string, lang: string) =>
    request<TemplateTranslation>(`/api/templates/${id}/translations/${lang}/approve`, {
      method: "POST",
    }),
  regenerateTranslation: (id: string, lang: string) =>
    request<TemplateTranslation>(`/api/templates/${id}/translations/${lang}/regenerate`, {
      method: "POST",
    }),
};

// Campaigns

export const campaignsApi = {
  create: (payload: CampaignCreate) =>
    request<Campaign>("/api/campaigns", { method: "POST", body: payload }),

  list: (page = 1, pageSize = 25) =>
    request<PaginatedResponse<Campaign>>(`/api/campaigns?page=${page}&page_size=${pageSize}`),

  get: (id: string) => request<Campaign>(`/api/campaigns/${id}`),

  importContacts: (id: string, file: File): Promise<ImportResult> => {
    const form = new FormData();
    form.append("file", file);
    return request<ImportResult>(`/api/campaigns/${id}/contacts/import`, {
      method: "POST",
      body: form,
      multipart: true,
    });
  },

  prepare: (id: string) =>
    request<{ status: string }>(`/api/campaigns/${id}/prepare`, { method: "POST" }),

  launch: (id: string) =>
    request<{ status: string }>(`/api/campaigns/${id}/launch`, { method: "POST" }),

  pause: (id: string) =>
    request<{ status: string }>(`/api/campaigns/${id}/pause`, { method: "POST" }),

  resume: (id: string) =>
    request<{ status: string }>(`/api/campaigns/${id}/resume`, { method: "POST" }),

  cancel: (id: string) =>
    request<{ status: string }>(`/api/campaigns/${id}/cancel`, { method: "POST" }),

  summary: (id: string) =>
    request<CampaignSummary>(`/api/campaigns/${id}/summary`),

  breakdown: (id: string, by: "language" | "segment") =>
    request<BreakdownResponse>(`/api/campaigns/${id}/breakdown?by=${by}`),

  contacts: (
    id: string,
    params: { outcome?: string; language?: string; segment?: string; page?: number; page_size?: number } = {}
  ) => {
    const qs = new URLSearchParams();
    if (params.outcome) qs.set("outcome", params.outcome);
    if (params.language) qs.set("language", params.language);
    if (params.segment) qs.set("segment", params.segment);
    if (params.page) qs.set("page", String(params.page));
    if (params.page_size) qs.set("page_size", String(params.page_size));
    const query = qs.toString() ? `?${qs}` : "";
    return request<PaginatedResponse<CampaignContact>>(`/api/campaigns/${id}/contacts${query}`);
  },

  retry: (
    id: string,
    payload: { outcomes?: string[]; languages?: string[]; segments?: string[] } = {}
  ) =>
    request<{ enqueued: number }>(`/api/campaigns/${id}/retry`, {
      method: "POST",
      body: payload,
    }),
};

// Overview

export const overviewApi = {
  get: () => request<Overview>("/api/overview"),
};

// Health

export const healthApi = {
  check: () => request<{ status: string }>("/healthz", { public: true }),
};