"use client";

/**
 * LaunchDrawer — custom slide-in panel for campaign launch.
 * Replaces browser alert() with a proper step-by-step launch flow:
 *   1. Channel detection
 *   2. Contacts loaded
 *   3. ElevenLabs TTS generation (optional)
 *   4. Calls dispatched
 */

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Step = { label: string; status: "pending" | "running" | "done" | "error"; detail?: string };

interface Props {
  campaign: { id: string; name: string; language?: string } | null;
  onClose: () => void;
  onSuccess: () => void;
}

export default function LaunchDrawer({ campaign, onClose, onSuccess }: Props) {
  // Prevent background scrolling when drawer is open
  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, []);

  const [steps, setSteps] = useState<Step[]>([]);
  const [done, setDone]   = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setStep = (i: number, update: Partial<Step>) =>
    setSteps(prev => prev.map((s, idx) => idx === i ? { ...s, ...update } : s));

  useEffect(() => {
    if (!campaign) return;

    const initial: Step[] = [
      { label: "Detecting channel",       status: "pending" },
      { label: "Loading contacts",        status: "pending" },
      { label: "Generating AI audio",     status: "pending" },
      { label: "Dispatching AI calls",    status: "pending" },
    ];
    setSteps(initial);
    setDone(false);
    setError(null);

    (async () => {
      try {
        // Step 0 — Channel detection
        setStep(0, { status: "running" });
        const chanRes = await fetch(`${API}/api/v1/campaigns/${campaign.id}/channel`);
        const chanData = chanRes.ok ? await chanRes.json() : {};
        const channel = chanData.selected_channel ?? "browser";
        setStep(0, { status: "done", detail: `Channel: ${channel}` });
        await delay(300);

        // Step 1 — Contacts
        setStep(1, { status: "running" });
        const cRes = await fetch(`${API}/api/v1/contacts/?campaign_id=${campaign.id}&limit=1`);
        const cData = cRes.ok ? await cRes.json() : [];
        const count = Array.isArray(cData) ? cData.length : (cData.total ?? "?");
        setStep(1, { status: "done", detail: `${count} contact(s) queued` });
        await delay(300);

        // Step 2 — TTS (best-effort, don't fail launch if missing)
        setStep(2, { status: "running" });
        try {
          const ttsRes = await fetch(`${API}/api/v1/campaigns/${campaign.id}/prepare-audio`, {
            method: "POST",
          });
          if (ttsRes.ok) {
            setStep(2, { status: "done", detail: "Audio clips ready" });
          } else {
            setStep(2, { status: "done", detail: "Using browser TTS fallback" });
          }
        } catch {
          setStep(2, { status: "done", detail: "Browser TTS fallback" });
        }
        await delay(300);

        // Step 3 — Launch
        setStep(3, { status: "running" });
        const launchRes = await fetch(`${API}/api/v1/campaigns/${campaign.id}/launch`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });
        if (!launchRes.ok) {
          const body = await launchRes.json().catch(() => ({}));
          throw new Error(body?.detail ?? `HTTP ${launchRes.status}`);
        }
        const launchData = await launchRes.json();
        setStep(3, { status: "done", detail: `${launchData.dispatched ?? "All"} calls dispatched via ${launchData.channel ?? channel}` });
        await delay(400);

        setDone(true);
        onSuccess();
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Launch failed";
        setError(msg);
        setSteps(prev => prev.map(s => s.status === "running" ? { ...s, status: "error" as const, detail: msg } : s));
      }
    })();
  }, [campaign]);

  if (!campaign) return null;

  const ICON: Record<Step["status"], string> = {
    pending: "○",
    running: "◌",
    done:    "✓",
    error:   "✗",
  };
  const COLOR: Record<Step["status"], string> = {
    pending: "#CBD5E1",
    running: "#F59E0B",
    done:    "#22C55E",
    error:   "#EF4444",
  };

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={done || error ? onClose : undefined}
        style={{
          position: "fixed", inset: 0, zIndex: 1000,
          background: "rgba(10,16,28,.55)",
          backdropFilter: "blur(3px)",
          cursor: done || error ? "pointer" : "default",
          transition: "opacity .2s",
        }}
      />

      {/* Drawer */}
      <div style={{
        position: "fixed", top: 0, bottom: 0, right: 0,
        width: "min(100vw, 460px)",
        zIndex: 1001,
        background: "#fff",
        boxShadow: "-8px 0 40px rgba(10,16,28,.18)",
        display: "flex", flexDirection: "column",
        fontFamily: "Manrope, sans-serif",
        animation: "slideInRight .28s cubic-bezier(.4,0,.2,1)",
      }}>
        <style>{`@keyframes slideInRight{from{transform:translateX(100%)}to{transform:translateX(0)}}`}</style>
        
        {/* Scrollable inner container */}
        <div style={{ padding: "28px 28px 36px", flex: 1, overflowY: "auto", minHeight: 0 }}>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: ".1em", color: "#8A9BB0", marginBottom: 4, textTransform: "uppercase" }}>
              Launching campaign
            </div>
            <h2 style={{ margin: 0, fontSize: 17, fontWeight: 800, color: "#17263A", letterSpacing: "-.03em", lineHeight: 1.3 }}>
              {campaign.name}
            </h2>
          </div>
          {(done || error) && (
            <button
              onClick={onClose}
              style={{ background: "rgba(23,38,58,.06)", border: "none", borderRadius: 8, width: 32, height: 32, cursor: "pointer", fontSize: 16, display: "flex", alignItems: "center", justifyContent: "center", color: "#5A6E84" }}
            >
              ✕
            </button>
          )}
        </div>

        {/* Steps */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14, marginBottom: 24 }}>
          {steps.map((step, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <span style={{
                width: 28, height: 28, borderRadius: 8,
                background: step.status === "done" ? "#DCFCE7" : step.status === "error" ? "#FEE2E2" : step.status === "running" ? "#FEF9C3" : "#F1F5F9",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 13, fontWeight: 800, color: COLOR[step.status],
                flexShrink: 0,
                animation: step.status === "running" ? "pulse 1s infinite" : "none",
              }}>
                {ICON[step.status]}
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: step.status === "error" ? "#DC2626" : "#17263A" }}>{step.label}</div>
                {step.detail && (
                  <div style={{ fontSize: 11, color: step.status === "error" ? "#DC2626" : "#8A9BB0", marginTop: 2 }}>{step.detail}</div>
                )}
              </div>
              {step.status === "running" && (
                <div style={{ width: 14, height: 14, border: "2px solid #FDE68A", borderTop: "2px solid #F59E0B", borderRadius: "50%", animation: "spin .7s linear infinite", flexShrink: 0 }} />
              )}
            </div>
          ))}
        </div>

        <style>{`
          @keyframes spin { to { transform: rotate(360deg); } }
          @keyframes pulse { 0%,100%{opacity:1}50%{opacity:.6} }
        `}</style>

        {/* Result */}
        {done && (
          <div style={{ background: "#F0FDF4", border: "1px solid #BBF7D0", borderRadius: 12, padding: "14px 18px", display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ fontSize: 22 }}>🚀</span>
            <div>
              <div style={{ fontSize: 13, fontWeight: 800, color: "#15803D" }}>Campaign launched!</div>
              <div style={{ fontSize: 11, color: "#16A34A", marginTop: 2 }}>AI calls are being dispatched to your contacts now.</div>
            </div>
          </div>
        )}

        {error && !done && (
          <div style={{ background: "#FFF1F2", border: "1px solid #FECDD3", borderRadius: 12, padding: "14px 18px" }}>
            <div style={{ fontSize: 13, fontWeight: 800, color: "#DC2626", marginBottom: 4 }}>Launch failed</div>
            <div style={{ fontSize: 11, color: "#E11D48" }}>{error}</div>
            <button
              onClick={onClose}
              style={{ marginTop: 12, background: "#DC2626", color: "#fff", border: "none", borderRadius: 8, padding: "8px 16px", fontSize: 12, fontWeight: 700, cursor: "pointer" }}
            >
              CLOSE
            </button>
          </div>
        )}
        </div>
      </div>
    </>
  );
}

function delay(ms: number) { return new Promise(r => setTimeout(r, ms)); }
