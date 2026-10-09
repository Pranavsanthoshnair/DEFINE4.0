"use client";

/**
 * Campaigns page — real backend + demo mode
 *
 * Real mode:  fetches from GET /api/v1/campaigns/
 * Demo mode:  shows hardcoded rich sample data
 *
 * Features:
 *  - CSV import contacts
 *  - Launch campaign (triggers ElevenLabs TTS + channel detection)
 *  - Browser call simulator
 *  - Live status polling for running campaigns
 */

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/ui/PageHeader";
import BrowserCallSimulator from "@/components/campaigns/BrowserCallSimulator";
import { useDemo } from "@/context/DemoModeContext";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// ── Demo data ──────────────────────────────────────────────────────────────

const DEMO_CAMPAIGNS = [
  { id: "demo-1", name: "Annual Tech Summit 2026 VIP Invite", status: "running", language: "en,hi,ta", contact_count: 2450, confirmed: 2063, rate: "84.2%" },
  { id: "demo-2", name: "Keynote RSVP Confirmation Wave 1",  status: "completed", language: "en,hi",    contact_count: 1200, confirmed: 1102, rate: "91.8%" },
  { id: "demo-3", name: "Workshop Reminder — Day 2",          status: "scheduled", language: "en,mr",    contact_count: 860,  confirmed: 0,    rate: "—" },
];

// ── Types ───────────────────────────────────────────────────────────────────

interface Campaign {
  id: string;
  name: string;
  status: string;
  language?: string;
  contact_count?: number;
  confirmed?: number;
  rate?: string;
}

// ── Status badge ────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const MAP: Record<string, { bg: string; color: string; dot?: boolean }> = {
    running:   { bg: "#dcfce7", color: "#16a34a", dot: true },
    completed: { bg: "#f3f4f6", color: "#374151" },
    scheduled: { bg: "#fef9c3", color: "#854d0e" },
    paused:    { bg: "#fef3c7", color: "#92400e" },
    failed:    { bg: "#fee2e2", color: "#991b1b" },
    draft:     { bg: "#f1f5f9", color: "#475569" },
  };
  const s = MAP[status] ?? { bg: "#f1f5f9", color: "#64748b" };
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5, background: s.bg, color: s.color, fontWeight: 700, fontSize: 10, padding: "3px 8px", borderRadius: 6, letterSpacing: ".06em", textTransform: "uppercase" }}>
      {s.dot && <span style={{ width: 6, height: 6, borderRadius: "50%", background: s.color, animation: "pulseRing 1.5s infinite" }} />}
      {status}
    </span>
  );
}

// ── Page ────────────────────────────────────────────────────────────────────

export default function CampaignsPage() {
  const { isDemo } = useDemo();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [simulatorId, setSimulatorId] = useState<string | null>(null);
  const [launching, setLaunching] = useState<string | null>(null);
  const [csvCampaignId, setCsvCampaignId] = useState<string | null>(null);
  const [csvStatus, setCsvStatus] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newLang, setNewLang] = useState("en");
  const [creating, setCreating] = useState(false);
  const csvRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Load campaigns ─────────────────────────────────────────────────────

  const load = useCallback(async () => {
    if (isDemo) {
      setCampaigns(DEMO_CAMPAIGNS);
      setLoading(false);
      return;
    }
    try {
      const res = await fetch(`${API}/api/v1/campaigns/`, {
        headers: { Accept: "application/json" },
        signal: AbortSignal.timeout(8000),
      });
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`HTTP ${res.status}: ${body.slice(0, 120)}`);
      }
      const data = await res.json();
      setCampaigns(Array.isArray(data) ? data : (data.items ?? data.campaigns ?? []));
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to load";
      // Ignore AbortError (timeout) silently — show empty state
      if ((e as Error)?.name !== "AbortError") setError(msg);
    } finally {
      setLoading(false);
    }
  }, [isDemo]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    load();
  }, [load]);

  // Poll running campaigns every 10s
  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (!isDemo && campaigns.some((c) => c.status === "running")) {
      pollRef.current = setInterval(load, 10000);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [campaigns, isDemo, load]);

  // ── Create campaign ─────────────────────────────────────────────────────

  const createCampaign = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const res = await fetch(`${API}/api/v1/campaigns/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName.trim(), language: newLang, status: "draft" }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const c = await res.json();
      setCampaigns((prev) => [c, ...prev]);
      setShowCreate(false);
      setNewName("");
    } catch (e) {
      alert(e instanceof Error ? e.message : "Create failed");
    } finally {
      setCreating(false);
    }
  };

  // ── Launch campaign ─────────────────────────────────────────────────────

  const launch = async (id: string) => {
    if (isDemo) { alert("🎭 Demo mode — launch disabled. Press Space\u00d75 to exit."); return; }
    setLaunching(id);
    try {
      const res = await fetch(`${API}/api/v1/campaigns/${id}/launch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? `Launch failed (${res.status})`);
      }
      await load();
      alert(`\u2705 Campaign launched! AI calls will start automatically.`);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Launch failed");
    } finally {
      setLaunching(null);
    }
  };

  // ── CSV import ──────────────────────────────────────────────────────────

  const handleCsv = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !csvCampaignId) return;
    setCsvStatus("Uploading\u2026");
    const form = new FormData();
    form.append("file", file);
    try {
      // Correct path: /api/v1/contacts/import (not import-csv)
      const res = await fetch(`${API}/api/v1/contacts/import?campaign_id=${csvCampaignId}`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? `HTTP ${res.status}`);
      }
      const data = await res.json();
      setCsvStatus(`\u2705 Imported ${data.imported ?? data.total ?? "?"} contacts`);
      await load();
    } catch (e) {
      setCsvStatus(e instanceof Error ? `\u274c ${e.message}` : "\u274c Import failed");
    }
    if (csvRef.current) csvRef.current.value = "";
  };

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto" }}>
      <PageHeader
        eyebrow="campaigns"
        title="Campaigns"
        subtitle="Create, launch, and track multilingual AI calling campaigns."
        mascot="girl"
        bubble={isDemo ? "Demo mode 🎭" : "Live data 🔴"}
        action={
          <button
            onClick={() => setShowCreate(true)}
            style={{ background: "#EA1D2C", color: "#fff", border: "none", borderRadius: 8, padding: "9px 18px", fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 13, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 8 }}
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M12 5v14M5 12h14"/></svg>
            New Campaign
          </button>
        }
      />

      {/* Create modal */}
      {showCreate && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(10,14,20,.5)", zIndex: 50, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ background: "#fff", borderRadius: 16, padding: "28px 32px", width: 400, maxWidth: "90vw", boxShadow: "0 24px 60px rgba(0,0,0,.2)" }}>
            <h2 style={{ fontFamily: "Manrope, sans-serif", fontWeight: 800, fontSize: 20, margin: "0 0 20px", color: "#17263A" }}>New Campaign</h2>
            <label style={{ display: "block", fontFamily: "Manrope, sans-serif", fontWeight: 600, fontSize: 13, color: "#5A6E84", marginBottom: 6 }}>Campaign Name</label>
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && createCampaign()}
              placeholder="e.g. Annual Summit 2026 Invites"
              style={{ width: "100%", border: "1.5px solid #e2e8f0", borderRadius: 8, padding: "10px 12px", fontFamily: "Manrope, sans-serif", fontSize: 14, marginBottom: 16, boxSizing: "border-box" }}
            />
            <label style={{ display: "block", fontFamily: "Manrope, sans-serif", fontWeight: 600, fontSize: 13, color: "#5A6E84", marginBottom: 6 }}>Primary Language</label>
            <select
              value={newLang}
              onChange={(e) => setNewLang(e.target.value)}
              style={{ width: "100%", border: "1.5px solid #e2e8f0", borderRadius: 8, padding: "10px 12px", fontFamily: "Manrope, sans-serif", fontSize: 14, marginBottom: 20, boxSizing: "border-box" }}
            >
              <option value="en">English</option>
              <option value="hi">Hindi</option>
              <option value="ta">Tamil</option>
              <option value="te">Telugu</option>
              <option value="kn">Kannada</option>
              <option value="ml">Malayalam</option>
              <option value="mr">Marathi</option>
            </select>
            <div style={{ display: "flex", gap: 10 }}>
              <button onClick={createCampaign} disabled={creating} style={{ flex: 1, background: "#EA1D2C", color: "#fff", border: "none", borderRadius: 8, padding: "11px", fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 14, cursor: creating ? "not-allowed" : "pointer" }}>
                {creating ? "Creating…" : "Create Campaign"}
              </button>
              <button onClick={() => setShowCreate(false)} style={{ padding: "11px 16px", background: "transparent", border: "1.5px solid #e2e8f0", borderRadius: 8, fontFamily: "Manrope, sans-serif", fontWeight: 600, fontSize: 14, cursor: "pointer" }}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* CSV status */}
      {csvStatus && (
        <div style={{ background: csvStatus.startsWith("✅") ? "#f0fdf4" : "#fef2f2", border: `1px solid ${csvStatus.startsWith("✅") ? "#86efac" : "#fca5a5"}`, borderRadius: 8, padding: "10px 16px", marginBottom: 16, fontFamily: "Manrope, sans-serif", fontSize: 13, fontWeight: 600, color: csvStatus.startsWith("✅") ? "#16a34a" : "#dc2626" }}>
          {csvStatus}
        </div>
      )}

      {/* Campaigns table */}
      <div style={{ background: "#fff", borderRadius: 16, border: "1px solid rgba(23,38,58,.08)", overflow: "hidden", boxShadow: "0 1px 4px rgba(23,38,58,.06)", marginBottom: 24 }}>
        {loading ? (
          <div style={{ padding: "48px 24px", textAlign: "center", color: "#8A9BB0", fontFamily: "Manrope, sans-serif" }}>Loading campaigns…</div>
        ) : error ? (
          <div style={{ padding: "48px 24px", textAlign: "center", color: "#EA1D2C", fontFamily: "Manrope, sans-serif", fontSize: 13 }}>
            {error} — <button onClick={load} style={{ color: "#EA1D2C", fontWeight: 700, background: "none", border: "none", cursor: "pointer" }}>Retry</button>
          </div>
        ) : campaigns.length === 0 ? (
          <div style={{ padding: "56px 24px", textAlign: "center" }}>
            <p style={{ fontFamily: "Manrope, sans-serif", fontSize: 16, fontWeight: 700, color: "#17263A", margin: "0 0 8px" }}>No campaigns yet</p>
            <p style={{ fontFamily: "Manrope, sans-serif", fontSize: 13, color: "#8A9BB0", margin: 0 }}>Create your first campaign above</p>
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#F8F9FA", borderBottom: "1px solid rgba(23,38,58,.08)" }}>
                {["Status", "Campaign Name", "Language", "Recipients", "Rate", "Actions"].map((h) => (
                  <th key={h} style={{ padding: "12px 16px", fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 11, color: "#8A9BB0", letterSpacing: ".08em", textTransform: "uppercase", textAlign: h === "Actions" ? "right" : "left" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {campaigns.map((c) => (
                <tr key={c.id} style={{ borderBottom: "1px solid rgba(23,38,58,.05)" }}>
                  <td style={{ padding: "14px 16px" }}><StatusBadge status={c.status} /></td>
                  <td style={{ padding: "14px 16px", fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 14, color: "#17263A" }}>{c.name}</td>
                  <td style={{ padding: "14px 16px", fontFamily: "Manrope, monospace", fontSize: 12, color: "#5A6E84" }}>{c.language ?? "—"}</td>
                  <td style={{ padding: "14px 16px", fontFamily: "Manrope, monospace", fontSize: 12, color: "#5A6E84" }}>{c.contact_count?.toLocaleString() ?? "—"}</td>
                  <td style={{ padding: "14px 16px", fontFamily: "Manrope, monospace", fontSize: 12, color: "#5A6E84" }}>{c.rate ?? "—"}</td>
                  <td style={{ padding: "14px 16px", textAlign: "right" }}>
                    <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", flexWrap: "wrap" }}>
                      {/* CSV Import */}
                      <button
                        title="Import contacts from CSV"
                        onClick={() => { setCsvCampaignId(c.id); setCsvStatus(null); csvRef.current?.click(); }}
                        style={{ padding: "6px 12px", background: "rgba(183,216,245,.3)", border: "1px solid rgba(23,38,58,.1)", borderRadius: 6, fontFamily: "Manrope, sans-serif", fontWeight: 600, fontSize: 11, cursor: "pointer", color: "#17263A" }}
                      >
                        📥 CSV
                      </button>
                      {/* Launch */}
                      {(c.status === "draft" || c.status === "scheduled" || c.status === "paused") && (
                        <button
                          onClick={() => launch(c.id)}
                          disabled={launching === c.id}
                          style={{ padding: "6px 12px", background: "#EA1D2C", color: "#fff", border: "none", borderRadius: 6, fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 11, cursor: launching === c.id ? "not-allowed" : "pointer" }}
                        >
                          {launching === c.id ? "⏳ Launching…" : "🚀 Launch"}
                        </button>
                      )}
                      {/* Simulator */}
                      <button
                        onClick={() => setSimulatorId(simulatorId === c.id ? null : c.id)}
                        style={{ padding: "6px 12px", background: simulatorId === c.id ? "#17263A" : "rgba(23,38,58,.06)", color: simulatorId === c.id ? "#fff" : "#17263A", border: "1px solid rgba(23,38,58,.12)", borderRadius: 6, fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 11, cursor: "pointer" }}
                      >
                        📞 Simulate
                      </button>
                      {/* View */}
                      <Link
                        href={`/campaigns/${c.id}`}
                        style={{ padding: "6px 12px", background: "transparent", color: "#EA1D2C", border: "1px solid rgba(234,29,44,.2)", borderRadius: 6, fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 11, textDecoration: "none" }}
                      >
                        View →
                      </Link>
                    </div>
                    {/* Inline simulator */}
                    {simulatorId === c.id && (
                      <div style={{ marginTop: 16, textAlign: "left" }}>
                        <BrowserCallSimulator
                          campaignId={c.id}
                          language={c.language?.split(",")[0] ?? "en"}
                          onComplete={(r) => console.info("[Veylo] call result", r)}
                        />
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Hidden file input */}
      <input ref={csvRef} type="file" accept=".csv" style={{ display: "none" }} onChange={handleCsv} />

      {/* Instructions */}
      <div style={{ background: "rgba(183,216,245,.2)", borderRadius: 12, padding: "16px 20px", fontFamily: "Manrope, sans-serif", fontSize: 13, color: "#5A6E84", border: "1px solid rgba(183,216,245,.4)" }}>
        <strong style={{ color: "#17263A" }}>How it works:</strong>
        {" "}Create a campaign → import contacts from CSV → click 🚀 Launch (auto-detects Telephony/Telegram/Browser) → ElevenLabs voice calls each contact → AI classifies their response → results appear in analytics.
        <br />
        <span style={{ fontSize: 11, opacity: 0.8 }}>Press Space×5 to toggle demo mode · Click 📞 Simulate to test the browser call flow</span>
      </div>
    </div>
  );
}
