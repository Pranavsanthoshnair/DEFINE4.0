/**
 * Centralised API client for Veylo — Member 4.
 *
 * CONTRACTS.md rules followed here:
 *  - Base URL from NEXT_PUBLIC_API_BASE_URL (§11 — exact variable name)
 *  - All paths start with /api/... with NO /v1/ prefix (§2 / §6)
 *  - Authorization: Bearer <JWT> on every authenticated request (§2)
 *  - Error body format: { "error": { "code", "message", "details" } } (§2)
 *  - 401 responses redirect the user to /login (§3 member-4 doc)
 *  - Pagination query: page (from 1) and page_size (§2)
 *
 * Token storage: the JWT is kept in sessionStorage (key: "veylo_token").
 * This is documented as the fallback approach — no httpOnly cookie proxy
 * was implemented yet (see member-4-frontend-devops.md §3 note on trade-off).
 * Switch to the /api/session route handler when time allows.
 *
 * Never log or display phone numbers, names, or transcripts — CONTRACTS.md §2.
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

// ── Base URL ─────────────────────────────────────────────────────────────────

/**
 * NEXT_PUBLIC_API_BASE_URL is the exact variable name from CONTRACTS.md §11.
 * Falls back to localhost:8100 which is the api service port in §12.
 */
const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8100";

// ── Token helpers ─────────────────────────────────────────────────────────────

const TOKEN_KEY = "veylo_token";

/** Store the JWT returned by /api/auth/login. */
export function setToken(token: string): void {
  if (typeof window !== "undefined") {
    sessionStorage.setItem(TOKEN_KEY, token);
  }
}

/** Retrieve the stored JWT, or null if not logged in. */
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(TOKEN_KEY);
}

/** Remove the JWT (called on logout or 401). */
export function clearToken(): void {
  if (typeof window !== "undefined") {
    sessionStorage.removeItem(TOKEN_KEY);
  }
}

// ── A typed error class so callers can distinguish API errors ─────────────────

export class ApiError extends Error {
  constructor(
    /** HTTP status code */
    public readonly status: number,
    /** contract error code string, e.g. "not_found" */
    public readonly code: string,
    message: string,
    public readonly details: Record<string, unknown> = {}
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ── Core request helper ───────────────────────────────────────────────────────

type RequestOptions = {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  /** Set to true for multipart (CSV upload). Omits Content-Type so fetch sets the boundary. */
  multipart?: boolean;
  /** Set to true to skip the Authorization header (used for public endpoints). */
  public?: boolean;
};

async function request<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = "GET", body, headers = {}, multipart = false } = options;

  const token = getToken();

  const requestHeaders: Record<string, string> = { ...headers };

  // Attach bearer token to every non-public request (CONTRACTS.md §2).
  if (!options.public && token) {
    requestHeaders["Authorization"] = `Bearer ${token}`;
  }

  // Only set Content-Type for JSON bodies; let the browser set it for multipart.
  if (!multipart && body !== undefined) {
    requestHeaders["Content-Type"] = "application/json";
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: requestHeaders,
    ...(body !== undefined
      ? { body: multipart ? (body as FormData) : JSON.stringify(body) }
      : {}),
  });

  // Redirect to /login on 401 — token expired or missing (member-4-frontend-devops.md §3).
  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new ApiError(401, "unauthorized", "Session expired. Please log in again.");
  }

  // 204 No Content — return undefined (used by DELETE /api/contacts/{id}).
  if (res.status === 204) return undefined as T;

  // Parse the response body for both success and error cases.
  let json: unknown;
  try {
    json = await res.json();
  } catch {
    // Non-JSON error body (e.g. a gateway error page).
    throw new ApiError(res.status, "parse_error", `HTTP ${res.status}: non-JSON response`);
  }

  if (!res.ok) {
    // Parse the contract error format: { "error": { "code", "message", "details" } }.
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

// ─────────────────────────────────────────────────────────────────────────────
// Auth — POST /api/auth/login, GET /api/auth/me
// ─────────────────────────────────────────────────────────────────────────────

export const authApi = {
  /**
   * Log in with email + password.
   * Stores the returned JWT automatically so subsequent calls include it.
   * CONTRACTS.md §6 — POST /api/auth/login (public, no auth required).
   */
  login: async (email: string, password: string): Promise<LoginResponse> => {
    const res = await request<LoginResponse>("/api/auth/login", {
      method: "POST",
      body: { email, password },
      public: true,
    });
    setToken(res.access_token);
    return res;
  },

  /** GET /api/auth/me — returns the current user from the token. */
  me: () => request<AuthUser>("/api/auth/me"),

  /** Clear the stored token (client-side logout). */
  logout: () => clearToken(),
};

// ─────────────────────────────────────────────────────────────────────────────
// Templates — GET /api/templates, GET /api/templates/{id}, translations
// ─────────────────────────────────────────────────────────────────────────────

export const templatesApi = {
  /** GET /api/templates — list all templates including presets. */
  list: () => request<Template[]>("/api/templates"),

  /** GET /api/templates/{id} */
  get: (id: string) => request<Template>(`/api/templates/${id}`),

  /**
   * GET /api/templates/{id}/translations
   * Returns translation status per language for the given template.
   */
  listTranslations: (id: string) =>
    request<TemplateTranslation[]>(`/api/templates/${id}/translations`),

  /**
   * PUT /api/templates/{id}/translations/{lang}
   * Body: { segments: { greeting: "...", prompt: "...", ... } }
   * Sets source=manual, status=draft.
   */
  saveTranslation: (id: string, lang: string, segments: Record<string, string>) =>
    request<TemplateTranslation>(`/api/templates/${id}/translations/${lang}`, {
      method: "PUT",
      body: { segments },
    }),

  /**
   * POST /api/templates/{id}/translations/{lang}/approve
   * Marks the translation as approved; records the approver.
   */
  approveTranslation: (id: string, lang: string) =>
    request<TemplateTranslation>(`/api/templates/${id}/translations/${lang}/approve`, {
      method: "POST",
    }),

  /**
   * POST /api/templates/{id}/translations/{lang}/regenerate
   * Triggers the AI service to re-translate this language.
   */
  regenerateTranslation: (id: string, lang: string) =>
    request<TemplateTranslation>(`/api/templates/${id}/translations/${lang}/regenerate`, {
      method: "POST",
    }),
};

// ─────────────────────────────────────────────────────────────────────────────
// Campaigns — CONTRACTS.md §6 Campaigns
// ─────────────────────────────────────────────────────────────────────────────

export const campaignsApi = {
  /**
   * POST /api/campaigns
   * Creates a new campaign in draft status.
   */
  create: (payload: CampaignCreate) =>
    request<Campaign>("/api/campaigns", { method: "POST", body: payload }),

  /**
   * GET /api/campaigns
   * Returns a paginated list of campaigns.
   */
  list: (page = 1, pageSize = 25) =>
    request<PaginatedResponse<Campaign>>(
      `/api/campaigns?page=${page}&page_size=${pageSize}`
    ),

  /**
   * GET /api/campaigns/{id}
   * Returns the campaign object plus a `readiness` object.
   */
  get: (id: string) => request<Campaign>(`/api/campaigns/${id}`),

  /**
   * POST /api/campaigns/{id}/contacts/import
   * Uploads a CSV file. Returns import counts and per-row errors.
   * Uses multipart/form-data so the fetch boundary is set automatically.
   */
  importContacts: (id: string, file: File): Promise<ImportResult> => {
    const form = new FormData();
    form.append("file", file);
    return request<ImportResult>(`/api/campaigns/${id}/contacts/import`, {
      method: "POST",
      body: form,
      multipart: true,
    });
  },

  /**
   * POST /api/campaigns/{id}/prepare
   * Starts translation for any missing languages and audio rendering.
   * Returns 202 { status: "preparing" }.
   */
  prepare: (id: string) =>
    request<{ status: string }>(`/api/campaigns/${id}/prepare`, { method: "POST" }),

  /**
   * POST /api/campaigns/{id}/launch
   * Requires campaign status to be "ready". Starts calling.
   */
  launch: (id: string) =>
    request<{ status: string }>(`/api/campaigns/${id}/launch`, { method: "POST" }),

  /** POST /api/campaigns/{id}/pause */
  pause: (id: string) =>
    request<{ status: string }>(`/api/campaigns/${id}/pause`, { method: "POST" }),

  /** POST /api/campaigns/{id}/resume */
  resume: (id: string) =>
    request<{ status: string }>(`/api/campaigns/${id}/resume`, { method: "POST" }),

  /** POST /api/campaigns/{id}/cancel */
  cancel: (id: string) =>
    request<{ status: string }>(`/api/campaigns/${id}/cancel`, { method: "POST" }),

  /**
   * GET /api/campaigns/{id}/summary
   * Returns totals, outcome counts, answer_rate and response_rate.
   * Poll this every 5 s while status is "running" or "preparing".
   */
  summary: (id: string) =>
    request<CampaignSummary>(`/api/campaigns/${id}/summary`),

  /**
   * GET /api/campaigns/{id}/breakdown?by=language|segment
   * Returns outcome stacked bars for charts.
   */
  breakdown: (id: string, by: "language" | "segment") =>
    request<BreakdownResponse>(`/api/campaigns/${id}/breakdown?by=${by}`),

  /**
   * GET /api/campaigns/{id}/contacts
   * Paginated list with optional filters for the dashboard contacts table.
   * Phone numbers are always masked — never request or store unmasked numbers.
   */
  contacts: (
    id: string,
    params: { outcome?: string; language?: string; segment?: string; page?: number; page_size?: number } = {}
  ) => {
    const qs = new URLSearchParams();
    if (params.outcome)    qs.set("outcome",    params.outcome);
    if (params.language)   qs.set("language",   params.language);
    if (params.segment)    qs.set("segment",    params.segment);
    if (params.page)       qs.set("page",       String(params.page));
    if (params.page_size)  qs.set("page_size",  String(params.page_size));
    const query = qs.toString() ? `?${qs}` : "";
    return request<PaginatedResponse<CampaignContact>>(
      `/api/campaigns/${id}/contacts${query}`
    );
  },

  /**
   * POST /api/campaigns/{id}/retry
   * Re-enqueues contacts matching the given outcomes/language/segment filters.
   * Default outcomes = NON_RESPONDER_SET (no_answer, busy, voicemail, no_input).
   */
  retry: (
    id: string,
    payload: { outcomes?: string[]; languages?: string[]; segments?: string[] } = {}
  ) =>
    request<{ enqueued: number }>(`/api/campaigns/${id}/retry`, {
      method: "POST",
      body: payload,
    }),
};

// ─────────────────────────────────────────────────────────────────────────────
// Overview — GET /api/overview
// ─────────────────────────────────────────────────────────────────────────────

export const overviewApi = {
  /** GET /api/overview — cross-campaign totals for the home page. */
  get: () => request<Overview>("/api/overview"),
};

// ─────────────────────────────────────────────────────────────────────────────
// Health — GET /healthz (public, no auth)
// ─────────────────────────────────────────────────────────────────────────────

export const healthApi = {
  check: () =>
    request<{ status: string }>("/healthz", { public: true }),
};
