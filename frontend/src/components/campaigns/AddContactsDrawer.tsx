"use client";

/**
 * AddContactsDrawer
 * Slide-up panel with two modes:
 *   • Single — add one contact with full details
 *   • Bulk CSV — drag-drop or pick a file
 *
 * When campaignId is null the drawer shows a campaign picker first.
 */

import { useEffect, useRef, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const LANGS = [
  { code: "en", label: "English" },
  { code: "hi", label: "Hindi" },
  { code: "ta", label: "Tamil" },
  { code: "te", label: "Telugu" },
  { code: "kn", label: "Kannada" },
  { code: "ml", label: "Malayalam" },
  { code: "mr", label: "Marathi" },
  { code: "bn", label: "Bengali" },
  { code: "gu", label: "Gujarati" },
  { code: "pa", label: "Punjabi" },
];

const SEGMENTS = ["VIP", "Speaker", "Sponsor", "Delegate", "Volunteer", "Press", "General"];

interface Props {
  campaignId: string | null;
  campaignName?: string;
  onClose: () => void;
  onSuccess: (count: number) => void;
}

type Tab = "single" | "csv";

type CampaignOption = { id: string; name: string };

export default function AddContactsDrawer({ campaignId: initialCampaignId, campaignName: initialCampaignName, onClose, onSuccess }: Props) {
  const [tab, setTab]             = useState<Tab>("single");
  const [status, setStatus]       = useState<"idle" | "loading" | "done" | "error">("idle");
  const [message, setMessage]     = useState<string>("");
  const [dragOver, setDragOver]   = useState(false);
  const csvRef = useRef<HTMLInputElement>(null);

  // ── Campaign picker (when no campaignId passed) ────────────────────────
  const [campaigns, setCampaigns]         = useState<CampaignOption[]>([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string>(initialCampaignId ?? "");
  const [campaignsLoading, setCampaignsLoading]     = useState(false);

  // Resolve which campaign is active
  const campaignId   = initialCampaignId ?? selectedCampaignId;
  const campaignName = initialCampaignId
    ? (initialCampaignName ?? "")
    : (campaigns.find(c => c.id === selectedCampaignId)?.name ?? "");

  useEffect(() => {
    if (initialCampaignId) return;          // already have one
    setCampaignsLoading(true);
    fetch(`${API}/api/v1/campaigns/?limit=50`)
      .then(r => r.ok ? r.json() : [])
      .then(d => setCampaigns(Array.isArray(d) ? d : []))
      .catch(() => {})
      .finally(() => setCampaignsLoading(false));
  }, [initialCampaignId]);

  // ── Single contact form state ──────────────────────────────────────────
  const [name, setName]       = useState("");
  const [phone, setPhone]     = useState("");
  const [lang, setLang]       = useState("en");
  const [segment, setSegment] = useState("General");
  const [notes, setNotes]     = useState("");

  const reset = () => {
    setStatus("idle"); setMessage("");
    setName(""); setPhone(""); setLang("en"); setSegment("General"); setNotes("");
  };

  // ── Submit single contact ──────────────────────────────────────────────
  const submitSingle = async () => {
    if (!campaignId) { setMessage("Please select a campaign first."); setStatus("error"); return; }
    if (!phone.trim()) { setMessage("Phone number is required."); setStatus("error"); return; }
    setStatus("loading"); setMessage("");
    try {
      const res = await fetch(`${API}/api/v1/contacts/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          campaign_id: campaignId,
          name: name.trim() || undefined,
          phone: phone.trim(),
          language: lang,
          segment: segment,
          notes: notes.trim() || undefined,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? `HTTP ${res.status}`);
      }
      setStatus("done"); setMessage(`✅ Contact added successfully!`);
      onSuccess(1);
    } catch (e) {
      setStatus("error"); setMessage(e instanceof Error ? e.message : "Failed to add contact");
    }
  };

  // ── Submit CSV ─────────────────────────────────────────────────────────
  const submitCsv = async (file: File) => {
    if (!campaignId) { setStatus("error"); setMessage("Please select a campaign first."); return; }
    setStatus("loading"); setMessage("Uploading…");
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch(`${API}/api/v1/contacts/import?campaign_id=${campaignId}`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? `HTTP ${res.status}`);
      }
      const data = await res.json();
      const n = data.imported ?? data.total ?? "?";
      setStatus("done"); setMessage(`✅ ${n} contacts imported!`);
      onSuccess(typeof n === "number" ? n : 0);
    } catch (e) {
      setStatus("error"); setMessage(e instanceof Error ? e.message : "Import failed");
    }
  };

  const handleFile = (file: File | undefined) => { if (file) submitCsv(file); };

  const inputStyle: React.CSSProperties = {
    width: "100%", border: "1.5px solid rgba(23,38,58,.12)", borderRadius: 8,
    padding: "9px 13px", fontFamily: "Manrope, sans-serif", fontSize: 13,
    boxSizing: "border-box", outline: "none", color: "#17263A",
  };
  const labelStyle: React.CSSProperties = {
    display: "block", fontFamily: "Manrope, sans-serif", fontSize: 11,
    fontWeight: 700, color: "#8A9BB0", letterSpacing: ".06em",
    textTransform: "uppercase", marginBottom: 5,
  };

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={status === "loading" ? undefined : onClose}
        style={{ position: "fixed", inset: 0, zIndex: 1000, background: "rgba(10,16,28,.5)", backdropFilter: "blur(3px)", cursor: "pointer" }}
      />

      {/* Drawer */}
      <div style={{
        position: "fixed", bottom: 0, right: 0,
        width: "min(100vw, 500px)",
        zIndex: 1001,
        background: "#fff",
        borderRadius: "20px 20px 0 0",
        boxShadow: "0 -8px 40px rgba(10,16,28,.18)",
        padding: "28px 28px 40px",
        fontFamily: "Manrope, sans-serif",
        maxHeight: "90vh",
        overflowY: "auto",
        animation: "slideUp .25s cubic-bezier(.4,0,.2,1)",
      }}>
        <style>{`@keyframes slideUp{from{transform:translateY(100%)}to{transform:translateY(0)}}`}</style>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: ".1em", color: "#8A9BB0", textTransform: "uppercase", marginBottom: 3 }}>
              Add Contacts
            </div>
            <h2 style={{ margin: 0, fontSize: 17, fontWeight: 800, color: "#17263A", letterSpacing: "-.03em" }}>
              {campaignName || "Select a campaign"}
            </h2>
          </div>
          <button onClick={onClose} style={{ background: "rgba(23,38,58,.06)", border: "none", borderRadius: 8, width: 32, height: 32, cursor: "pointer", fontSize: 16, display: "flex", alignItems: "center", justifyContent: "center", color: "#5A6E84" }}>✕</button>
        </div>

        {/* Campaign picker — only shown when no campaign was pre-selected */}
        {!initialCampaignId && (
          <div style={{ marginBottom: 20 }}>
            <label style={{ display: "block", fontFamily: "Manrope, sans-serif", fontSize: 11, fontWeight: 700, color: "#8A9BB0", letterSpacing: ".06em", textTransform: "uppercase", marginBottom: 6 }}>
              Campaign <span style={{ color: "#EA1D2C" }}>*</span>
            </label>
            {campaignsLoading ? (
              <div style={{ fontFamily: "Manrope, sans-serif", fontSize: 13, color: "#8A9BB0", padding: "9px 0" }}>Loading campaigns…</div>
            ) : campaigns.length === 0 ? (
              <div style={{ fontFamily: "Manrope, sans-serif", fontSize: 13, color: "#EA1D2C", padding: "9px 0" }}>No campaigns found — create one first.</div>
            ) : (
              <select
                value={selectedCampaignId}
                onChange={e => setSelectedCampaignId(e.target.value)}
                style={{ width: "100%", border: "1.5px solid rgba(23,38,58,.12)", borderRadius: 8, padding: "9px 13px", fontFamily: "Manrope, sans-serif", fontSize: 13, color: "#17263A", boxSizing: "border-box" }}
              >
                <option value="">— Select campaign —</option>
                {campaigns.map(c => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            )}
          </div>
        )}

        {/* Tabs */}
        <div style={{ display: "flex", gap: 4, background: "#F1F5F9", borderRadius: 10, padding: 4, marginBottom: 22 }}>
          {(["single", "csv"] as Tab[]).map(t => (
            <button
              key={t}
              onClick={() => { setTab(t); reset(); }}
              style={{
                flex: 1, padding: "8px 0", border: "none", borderRadius: 7, cursor: "pointer",
                fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 12, letterSpacing: ".02em",
                background: tab === t ? "#fff" : "transparent",
                color: tab === t ? "#17263A" : "#8A9BB0",
                boxShadow: tab === t ? "0 1px 4px rgba(23,38,58,.10)" : "none",
                transition: "all .15s",
              }}
            >
              {t === "single" ? "👤 Single Contact" : "📂 Bulk CSV"}
            </button>
          ))}
        </div>

        {/* ── Single contact form ──────────────────────────────────────── */}
        {tab === "single" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div>
                <label style={labelStyle}>Full Name</label>
                <input value={name} onChange={e => setName(e.target.value)} placeholder="Arjun Sharma" style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Phone Number <span style={{ color: "#EA1D2C" }}>*</span></label>
                <input value={phone} onChange={e => setPhone(e.target.value)} placeholder="+91 98765 43210" style={inputStyle} type="tel" />
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div>
                <label style={labelStyle}>Language</label>
                <select value={lang} onChange={e => setLang(e.target.value)} style={inputStyle}>
                  {LANGS.map(l => <option key={l.code} value={l.code}>{l.label}</option>)}
                </select>
              </div>
              <div>
                <label style={labelStyle}>Segment</label>
                <select value={segment} onChange={e => setSegment(e.target.value)} style={inputStyle}>
                  {SEGMENTS.map(s => <option key={s}>{s}</option>)}
                </select>
              </div>
            </div>

            <div>
              <label style={labelStyle}>Notes <span style={{ color: "#CBD5E1", fontWeight: 400 }}>(optional)</span></label>
              <textarea
                value={notes} onChange={e => setNotes(e.target.value)}
                placeholder="e.g. Keynote speaker, prefers morning calls"
                rows={2}
                style={{ ...inputStyle, resize: "vertical", minHeight: 60 }}
              />
            </div>

            {/* CSV hint */}
            <div style={{ background: "#F8FAFC", borderRadius: 8, padding: "10px 14px", fontSize: 11, color: "#8A9BB0", border: "1px dashed rgba(23,38,58,.12)" }}>
              Adding multiple contacts? Switch to <button onClick={() => setTab("csv")} style={{ background: "none", border: "none", color: "#EA1D2C", fontWeight: 700, fontSize: 11, cursor: "pointer", padding: 0 }}>Bulk CSV →</button>
            </div>

            {/* Status */}
            {message && (
              <div style={{ background: status === "done" ? "#F0FDF4" : "#FFF1F2", border: `1px solid ${status === "done" ? "#BBF7D0" : "#FECDD3"}`, borderRadius: 8, padding: "10px 14px", fontSize: 12, fontWeight: 600, color: status === "done" ? "#15803D" : "#DC2626" }}>
                {message}
              </div>
            )}

            <div style={{ display: "flex", gap: 10, marginTop: 4 }}>
              {status === "done" ? (
                <>
                  <button onClick={reset} style={{ flex: 1, background: "#17263A", color: "#fff", border: "none", borderRadius: 8, padding: 11, fontWeight: 700, fontSize: 13, cursor: "pointer" }}>
                    + Add Another
                  </button>
                  <button onClick={onClose} style={{ flex: 1, background: "#EA1D2C", color: "#fff", border: "none", borderRadius: 8, padding: 11, fontWeight: 700, fontSize: 13, cursor: "pointer" }}>
                    Done ✓
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={submitSingle}
                    disabled={status === "loading"}
                    style={{ flex: 1, background: "#EA1D2C", color: "#fff", border: "none", borderRadius: 8, padding: 11, fontWeight: 700, fontSize: 13, cursor: status === "loading" ? "not-allowed" : "pointer", opacity: status === "loading" ? .7 : 1 }}
                  >
                    {status === "loading" ? "Adding…" : "Add Contact"}
                  </button>
                  <button onClick={onClose} style={{ padding: "11px 18px", background: "transparent", border: "1.5px solid rgba(23,38,58,.12)", borderRadius: 8, fontWeight: 700, fontSize: 13, cursor: "pointer" }}>Cancel</button>
                </>
              )}
            </div>
          </div>
        )}

        {/* ── CSV bulk upload ────────────────────────────────────────── */}
        {tab === "csv" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Drop zone */}
            <div
              onDragOver={e => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={e => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files[0]); }}
              onClick={() => csvRef.current?.click()}
              style={{
                border: `2px dashed ${dragOver ? "#EA1D2C" : "rgba(23,38,58,.15)"}`,
                borderRadius: 12, padding: "36px 24px", textAlign: "center",
                cursor: "pointer", transition: "all .15s",
                background: dragOver ? "#FFF1F2" : "#FAFBFC",
              }}
            >
              <div style={{ fontSize: 32, marginBottom: 10 }}>{status === "loading" ? "⏳" : "📂"}</div>
              <p style={{ margin: "0 0 6px", fontWeight: 700, fontSize: 14, color: "#17263A" }}>
                {status === "loading" ? "Uploading…" : "Drop your CSV here or click to browse"}
              </p>
              <p style={{ margin: 0, fontSize: 11, color: "#8A9BB0" }}>Max 50 MB · UTF-8 encoding</p>
              <input ref={csvRef} type="file" accept=".csv" style={{ display: "none" }} onChange={e => handleFile(e.target.files?.[0])} />
            </div>

            {/* CSV format guide */}
            <div style={{ background: "#F8FAFC", borderRadius: 10, padding: "14px 16px", border: "1px solid rgba(23,38,58,.07)" }}>
              <p style={{ margin: "0 0 8px", fontWeight: 700, fontSize: 12, color: "#17263A" }}>Required CSV format</p>
              <code style={{ display: "block", fontSize: 11, color: "#5A6E84", background: "rgba(23,38,58,.04)", borderRadius: 6, padding: "8px 10px", fontFamily: "monospace", overflowX: "auto" }}>
                name,phone,language,segment,notes<br />
                Arjun Sharma,+919876543210,hi,VIP,Keynote speaker<br />
                Priya Nair,+919123456789,ta,General,<br />
              </code>
              <p style={{ margin: "8px 0 0", fontSize: 10, color: "#A0AEC0" }}>
                • <strong>phone</strong> is required (E.164 format recommended)<br />
                • <strong>language</strong>: en hi ta te kn ml mr bn gu pa<br />
                • <strong>segment</strong>: VIP Speaker Sponsor Delegate Volunteer General
              </p>
            </div>

            {/* Status */}
            {message && (
              <div style={{ background: status === "done" ? "#F0FDF4" : "#FFF1F2", border: `1px solid ${status === "done" ? "#BBF7D0" : "#FECDD3"}`, borderRadius: 8, padding: "12px 16px", fontSize: 13, fontWeight: 600, color: status === "done" ? "#15803D" : "#DC2626" }}>
                {message}
              </div>
            )}

            {status === "done" && (
              <button onClick={onClose} style={{ width: "100%", background: "#EA1D2C", color: "#fff", border: "none", borderRadius: 8, padding: 12, fontWeight: 700, fontSize: 14, cursor: "pointer" }}>
                Done ✓
              </button>
            )}
          </div>
        )}
      </div>
    </>
  );
}
