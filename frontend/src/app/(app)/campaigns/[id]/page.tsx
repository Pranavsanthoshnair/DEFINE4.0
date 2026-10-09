"use client";
import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import PageHeader from "@/components/ui/PageHeader";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Campaign {
  id: string;
  name: string;
  description?: string;
  language: string;
  status: string;
  created_at: string;
}

interface CallRecord {
  id: string;
  campaign_id?: string;
  status: string;
  outcome?: string;
  duration_sec?: number;
  created_at: string;
}

interface ImportResult {
  queued: number;
  skipped: number;
  errors: string[];
}

interface LaunchResult {
  channel: string;
  provider?: string;
  contacts_total: number;
  calls_placed?: number;
  calls_failed?: number;
  calls_skipped_no_phone?: number;
  audio_segments_ready?: number;
  error?: string;
  warning?: string;
}

const STATUS_COLORS: Record<string, string> = {
  draft: "#8B949E",
  ready: "#3FB950",
  scheduled: "#58A6FF",
  running: "#F78166",
  paused: "#D29922",
  completed: "#3FB950",
  cancelled: "#6E7681",
};

const OUTCOME_COLORS: Record<string, string> = {
  confirmed: "#3FB950",
  declined: "#F78166",
  no_answer: "#D29922",
  busy: "#8B949E",
  failed: "#F78166",
  unclear: "#8B949E",
};

export default function CampaignDetailPage() {
  const params = useParams();
  const router = useRouter();
  const campaignId = params.id as string;

  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [calls, setCalls] = useState<CallRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [importError, setImportError] = useState("");

  const [launching, setLaunching] = useState(false);
  const [launchResult, setLaunchResult] = useState<LaunchResult | null>(null);
  const [launchError, setLaunchError] = useState("");

  const [channel, setChannel] = useState<{ selected_channel: string; telephony_provider: string } | null>(null);

  const fileRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchCampaign = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/campaigns/${campaignId}`);
      if (!res.ok) {
        setError("Campaign not found or database not connected.");
        return;
      }
      setCampaign(await res.json());
    } catch {
      setError("Could not reach the backend. Make sure uvicorn is running.");
    }
  }, [campaignId]);

  const fetchCalls = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/calls/?campaign_id=${campaignId}&limit=100`);
      if (res.ok) setCalls(await res.json());
    } catch { /* non-fatal */ }
  }, [campaignId]);

  const fetchChannel = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/campaigns/${campaignId}/channel`);
      if (res.ok) setChannel(await res.json());
    } catch { /* non-fatal */ }
  }, [campaignId]);

  useEffect(() => {
    (async () => {
      setLoading(true);
      await Promise.all([fetchCampaign(), fetchCalls(), fetchChannel()]);
      setLoading(false);
    })();
  }, [fetchCampaign, fetchCalls, fetchChannel]);

  // Poll calls every 5s while campaign is running
  useEffect(() => {
    if (campaign?.status === "running") {
      pollRef.current = setInterval(() => {
        fetchCalls();
        fetchCampaign();
      }, 5000);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [campaign?.status, fetchCalls, fetchCampaign]);

  const handleCSVUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    setImportResult(null);
    setImportError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(
        `${API}/api/v1/contacts/import-to-campaign?campaign_id=${campaignId}`,
        { method: "POST", body: form }
      );
      const data = await res.json();
      if (!res.ok) {
        setImportError(data.detail || "Import failed.");
      } else {
        setImportResult(data);
        await fetchCampaign();
      }
    } catch {
      setImportError("Network error during import.");
    } finally {
      setImporting(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const handleLaunch = async () => {
    setLaunching(true);
    setLaunchResult(null);
    setLaunchError("");
    try {
      const res = await fetch(`${API}/api/v1/campaigns/${campaignId}/launch`, {
        method: "POST",
      });
      const data = await res.json();
      if (!res.ok) {
        setLaunchError(data.detail || JSON.stringify(data));
      } else {
        setLaunchResult(data);
        await fetchCampaign();
        await fetchCalls();
      }
    } catch {
      setLaunchError("Network error when launching campaign.");
    } finally {
      setLaunching(false);
    }
  };

  // KPI counts from calls
  const kpis = {
    confirmed: calls.filter((c) => c.outcome === "confirmed").length,
    declined: calls.filter((c) => c.outcome === "declined").length,
    no_answer: calls.filter((c) => ["no_answer", "busy"].includes(c.outcome || "")).length,
    total: calls.length,
  };
  const progress = kpis.confirmed + kpis.declined;

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "60vh" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ width: 40, height: 40, border: "3px solid rgba(255,255,255,.15)", borderTopColor: "var(--red)", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 12px" }} />
          <p style={{ color: "#8B949E", font: "600 13px 'Manrope'" }}>Loading campaign…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ maxWidth: 600, margin: "60px auto", padding: "0 24px" }}>
        <div className="glass" style={{ padding: "28px 24px", textAlign: "center" }}>
          <p style={{ color: "#F78166", font: "700 15px 'Manrope'", marginBottom: 8 }}>⚠ {error}</p>
          <Link href="/campaigns" className="vbtn" style={{ textDecoration: "none", display: "inline-block", marginTop: 12 }}>
            ← Back to campaigns
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="page-in" style={{ maxWidth: 1180, margin: "0 auto", padding: "30px 28px 80px" }}>
      <PageHeader
        eyebrow="campaign detail"
        title={campaign?.name || `Campaign #${campaignId.slice(0, 8)}`}
        subtitle={campaign?.description || "Outbound calling campaign — ready to launch."}
        tagline={`Language: ${campaign?.language?.toUpperCase() || "EN"}`}
        bubble={campaign?.status === "running" ? "Calling!" : "Ready"}
        mascot="boy"
        action={
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Link href="/campaigns" className="vbtn" style={{ textDecoration: "none", opacity: 0.7, fontSize: 13 }}>
              ← Campaigns
            </Link>
            {/* Status badge */}
            <span style={{
              background: `${STATUS_COLORS[campaign?.status || "draft"]}22`,
              color: STATUS_COLORS[campaign?.status || "draft"],
              border: `1px solid ${STATUS_COLORS[campaign?.status || "draft"]}55`,
              borderRadius: 20,
              padding: "4px 12px",
              font: "700 12px 'Manrope'",
              display: "flex",
              alignItems: "center",
              gap: 5,
            }}>
              {campaign?.status === "running" && <span style={{ width: 7, height: 7, borderRadius: "50%", background: "currentColor", display: "inline-block", animation: "pulse 1s ease-in-out infinite" }} />}
              {campaign?.status?.toUpperCase() || "DRAFT"}
            </span>
          </div>
        }
      />

      {/* Provider / Channel info strip */}
      {channel && (
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 16px", background: "rgba(58,166,80,.08)", border: "1px solid rgba(58,166,80,.2)", borderRadius: 10, marginBottom: "var(--gap)", font: "600 13px 'Manrope'", color: "#3FB950" }}>
          <span>📡</span>
          <span>
            Active channel: <b>{channel.selected_channel.toUpperCase()}</b>
            {channel.telephony_provider && channel.telephony_provider !== "mock" && (
              <> · Provider: <b>{channel.telephony_provider.toUpperCase()}</b></>
            )}
            {(channel.telephony_provider === "mock" || !channel.selected_channel) && (
              <span style={{ color: "#D29922" }}> · ⚠ No telephony credentials — will use mock/browser mode</span>
            )}
          </span>
        </div>
      )}

      {/* Progress bar */}
      <div className="glass" style={{ padding: "18px 20px", marginBottom: "var(--gap)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", font: "700 13px 'Manrope'", marginBottom: 8 }}>
          <span>Call progress</span>
          <span>{progress} / {kpis.total} responses</span>
        </div>
        <div className="sbar">
          <span className="sbar-seg" style={{ width: kpis.total ? `${(kpis.confirmed / kpis.total) * 100}%` : "0%", background: "#3FB950" }} />
          <span className="sbar-seg" style={{ width: kpis.total ? `${(kpis.declined / kpis.total) * 100}%` : "0%", background: "#F78166" }} />
          <span className="sbar-seg" style={{ width: kpis.total ? `${(kpis.no_answer / kpis.total) * 100}%` : "100%", background: "rgba(183,216,245,.25)" }} />
        </div>
      </div>

      {/* KPI row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(130px,1fr))", gap: "var(--gap)", marginBottom: "var(--gap)" }}>
        {[
          { label: "Confirmed", v: kpis.confirmed, color: "#3FB950" },
          { label: "Declined", v: kpis.declined, color: "#F78166" },
          { label: "Unanswered", v: kpis.no_answer, color: "#D29922" },
          { label: "Total calls", v: kpis.total, color: "#58A6FF" },
        ].map((k) => (
          <div key={k.label} className="glass" style={{ padding: "18px 20px", borderLeft: `3px solid ${k.color}` }}>
            <span className="kpi-val" style={{ color: k.color }}>{k.v}</span>
            <span className="kpi-lbl">{k.label}</span>
          </div>
        ))}
      </div>

      {/* Two column: Actions + Call log */}
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) minmax(0,1.4fr)", gap: "var(--gap)" }}>

        {/* LEFT: Upload + Launch */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap)" }}>

          {/* Step 1: Upload CSV */}
          <div className="glass" style={{ padding: "22px 20px" }}>
            <h3 style={{ font: "800 16px 'Manrope'", letterSpacing: "-.02em", margin: "0 0 4px" }}>
              Step 1 — Upload Contacts
            </h3>
            <p style={{ font: "500 12px 'Manrope'", color: "#8B949E", margin: "0 0 14px" }}>
              CSV must have a <code style={{ background: "rgba(255,255,255,.08)", padding: "1px 5px", borderRadius: 4 }}>phone</code> column.
              Optional: <code style={{ background: "rgba(255,255,255,.08)", padding: "1px 5px", borderRadius: 4 }}>language</code>, <code style={{ background: "rgba(255,255,255,.08)", padding: "1px 5px", borderRadius: 4 }}>name</code>
            </p>

            <label style={{ display: "block", cursor: importing ? "not-allowed" : "pointer" }}>
              <div style={{
                border: "2px dashed rgba(255,255,255,.15)",
                borderRadius: 10,
                padding: "20px",
                textAlign: "center",
                transition: "all .2s",
                background: importing ? "rgba(255,255,255,.03)" : "transparent",
              }}>
                {importing ? (
                  <p style={{ font: "600 13px 'Manrope'", color: "#8B949E", margin: 0 }}>⏳ Importing…</p>
                ) : (
                  <>
                    <p style={{ font: "700 14px 'Manrope'", margin: "0 0 4px" }}>📂 Drop CSV here or click to browse</p>
                    <p style={{ font: "500 11px 'Manrope'", color: "#8B949E", margin: 0 }}>Max 10 MB · UTF-8 encoded</p>
                  </>
                )}
              </div>
              <input
                ref={fileRef}
                type="file"
                accept=".csv"
                onChange={handleCSVUpload}
                disabled={importing}
                style={{ display: "none" }}
              />
            </label>

            {importResult && (
              <div style={{ marginTop: 12, padding: "10px 14px", background: "rgba(58,166,80,.1)", border: "1px solid rgba(58,166,80,.25)", borderRadius: 8, font: "600 13px 'Manrope'" }}>
                ✅ <b>{importResult.queued}</b> contacts queued · {importResult.skipped} skipped
                {importResult.errors.length > 0 && (
                  <div style={{ color: "#D29922", marginTop: 6, font: "500 11px 'Manrope'" }}>
                    {importResult.errors.slice(0, 3).join(" · ")}
                  </div>
                )}
              </div>
            )}
            {importError && (
              <div style={{ marginTop: 12, padding: "10px 14px", background: "rgba(247,129,102,.1)", border: "1px solid rgba(247,129,102,.25)", borderRadius: 8, font: "600 12px 'Manrope'", color: "#F78166" }}>
                ⚠ {importError}
              </div>
            )}
          </div>

          {/* Step 2: Launch */}
          <div className="glass" style={{ padding: "22px 20px" }}>
            <h3 style={{ font: "800 16px 'Manrope'", letterSpacing: "-.02em", margin: "0 0 4px" }}>
              Step 2 — Launch Campaign
            </h3>
            <p style={{ font: "500 12px 'Manrope'", color: "#8B949E", margin: "0 0 14px" }}>
              Places calls to all pending contacts using the active telephony provider.
              {channel?.selected_channel === "telephony"
                ? ` Will use ${channel.telephony_provider?.toUpperCase()}.`
                : " No telephony detected — will use browser simulation."}
            </p>

            <button
              className="vbtn"
              onClick={handleLaunch}
              disabled={launching || campaign?.status === "running"}
              style={{
                width: "100%",
                opacity: (launching || campaign?.status === "running") ? 0.5 : 1,
                cursor: (launching || campaign?.status === "running") ? "not-allowed" : "pointer",
                fontSize: 15,
                padding: "14px 20px",
              }}
            >
              {launching ? "⏳ Launching…" : campaign?.status === "running" ? "🔄 Already Running" : "🚀 Launch Calls"}
            </button>

            {launchResult && (
              <div style={{ marginTop: 12, padding: "12px 14px", background: "rgba(58,166,80,.1)", border: "1px solid rgba(58,166,80,.25)", borderRadius: 8, font: "600 13px 'Manrope'" }}>
                {launchResult.error ? (
                  <span style={{ color: "#F78166" }}>⚠ {launchResult.error}</span>
                ) : launchResult.warning ? (
                  <span style={{ color: "#D29922" }}>⚠ {launchResult.warning}</span>
                ) : (
                  <>
                    ✅ <b>{launchResult.calls_placed ?? launchResult.contacts_total}</b> calls placed
                    via {(launchResult.provider || launchResult.channel || "").toUpperCase()}
                    {launchResult.calls_failed !== undefined && launchResult.calls_failed > 0 && (
                      <span style={{ color: "#D29922" }}> · {launchResult.calls_failed} failed</span>
                    )}
                  </>
                )}
              </div>
            )}
            {launchError && (
              <div style={{ marginTop: 12, padding: "10px 14px", background: "rgba(247,129,102,.1)", border: "1px solid rgba(247,129,102,.25)", borderRadius: 8, font: "600 12px 'Manrope'", color: "#F78166" }}>
                ⚠ {launchError}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT: Call log */}
        <div className="glass" style={{ padding: "22px 20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <h3 style={{ font: "800 16px 'Manrope'", letterSpacing: "-.02em", margin: 0 }}>
              Live Call Log
            </h3>
            <button
              onClick={fetchCalls}
              style={{ background: "transparent", border: "1px solid rgba(255,255,255,.12)", borderRadius: 6, padding: "4px 10px", font: "600 11px 'Manrope'", color: "#8B949E", cursor: "pointer" }}
            >
              ↻ Refresh
            </button>
          </div>

          {calls.length === 0 ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "32px 0", gap: 10 }}>
              <span style={{ fontSize: 36, opacity: .4 }}>📞</span>
              <p style={{ font: "600 13px 'Manrope'", color: "#8B949E", margin: 0, textAlign: "center" }}>
                No calls yet.<br />
                <span style={{ font: "500 12px 'Manrope'" }}>Upload a CSV and launch to begin.</span>
              </p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 420, overflowY: "auto" }}>
              {calls.map((call) => (
                <div key={call.id} style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "10px 12px",
                  background: "rgba(255,255,255,.04)",
                  borderRadius: 8,
                  borderLeft: `3px solid ${OUTCOME_COLORS[call.outcome || ""] || "#8B949E"}`,
                }}>
                  <div>
                    <span style={{ font: "700 12px 'Manrope'", color: OUTCOME_COLORS[call.outcome || ""] || "#8B949E" }}>
                      {call.outcome ? call.outcome.replace("_", " ").toUpperCase() : call.status.toUpperCase()}
                    </span>
                    <div style={{ font: "500 11px 'Manrope'", color: "#6E7681", marginTop: 1 }}>
                      {new Date(call.created_at).toLocaleTimeString()}
                      {call.duration_sec ? ` · ${call.duration_sec}s` : ""}
                    </div>
                  </div>
                  <span style={{ font: "600 11px 'Manrope'", color: "#6E7681", fontFamily: "monospace" }}>
                    {call.id.slice(0, 8)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
      `}</style>
      <div className="pgf"><span>VEYLO / CAMPAIGN DETAIL</span><i>✳</i></div>
    </div>
  );
}
