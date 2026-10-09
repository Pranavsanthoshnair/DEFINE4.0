"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/ui/PageHeader";
import BrowserCallSimulator from "@/components/campaigns/BrowserCallSimulator";
import LaunchDrawer from "@/components/campaigns/LaunchDrawer";
import AddContactsDrawer from "@/components/campaigns/AddContactsDrawer";
import { useDemo } from "@/context/DemoModeContext";
import { DEMO_CAMPAIGNS } from "@/lib/demo-data";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

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
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);
  const [simulatorId, setSimulatorId]   = useState<string | null>(null);
  const [launchTarget, setLaunchTarget] = useState<Campaign | null>(null);
  const [addContactsCampaign, setAddContactsCampaign] = useState<Campaign | null>(null);
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

  // ── Launch campaign — opens the custom LaunchDrawer ─────────────────────

  const launch = (campaign: Campaign) => {
    if (isDemo) {
      setLaunchTarget({ id: "demo-preview", name: campaign.name, language: campaign.language, status: "draft" });
      return;
    }
    setLaunchTarget(campaign);
  };

  // ── CSV import — now handled inside AddContactsDrawer ──────────────────

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
          <Link
            href="/campaigns/new"
            style={{ textDecoration: "none", background: "#EA1D2C", color: "#fff", border: "none", borderRadius: 8, padding: "9px 18px", fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 13, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 8 }}
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M12 5v14M5 12h14"/></svg>
            New Campaign
          </Link>
        }
      />


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
                      {/* Add Contacts */}
                      <button
                        title="Add contacts to this campaign"
                        onClick={() => setAddContactsCampaign(c)}
                        style={{ padding: "6px 12px", background: "rgba(183,216,245,.3)", border: "1px solid rgba(23,38,58,.1)", borderRadius: 6, fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 11, cursor: "pointer", color: "#17263A" }}
                      >
                        👤 Add Contacts
                      </button>
                      {/* Launch */}
                      {(c.status === "draft" || c.status === "scheduled" || c.status === "paused") && (
                        <button
                          onClick={() => launch(c)}
                          style={{ padding: "6px 12px", background: "#EA1D2C", color: "#fff", border: "none", borderRadius: 6, fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 11, cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}
                        >
                          🚀 Launch
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

      {/* Custom launch drawer */}
      {launchTarget && (
        <LaunchDrawer
          campaign={launchTarget}
          onClose={() => setLaunchTarget(null)}
          onSuccess={() => { setLaunchTarget(null); load(); }}
        />
      )}

      {/* Add contacts drawer — single or bulk CSV */}
      {addContactsCampaign && (
        <AddContactsDrawer
          campaignId={addContactsCampaign.id}
          campaignName={addContactsCampaign.name}
          onClose={() => setAddContactsCampaign(null)}
          onSuccess={() => { setAddContactsCampaign(null); load(); }}
        />
      )}
    </div>
  );
}
