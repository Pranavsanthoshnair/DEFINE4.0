"use client";

/**
 * AddContactsDrawer
 * Slide-in panel (from right) with two modes:
 *   • Single — add one contact with full details (Name, Phone, Language, Organization / Segment, Notes)
 *   • Bulk CSV — drag-drop, preview and upload with automatic validation and sample template download.
 *
 * When campaignId is null the drawer defaults to General Audience with optional campaign selection.
 */

import { useEffect, useRef, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const LANGS = [
  { code: "en", label: "English" },
  { code: "hi", label: "Hindi (हिंदी)" },
  { code: "ta", label: "Tamil (தமிழ்)" },
  { code: "te", label: "Telugu (తెలుగు)" },
  { code: "kn", label: "Kannada (ಕನ್ನಡ)" },
  { code: "ml", label: "Malayalam (മലയാളം)" },
  { code: "mr", label: "Marathi (मराठी)" },
  { code: "bn", label: "Bengali (বাংলা)" },
  { code: "gu", label: "Gujarati (ગુજરાતી)" },
  { code: "pa", label: "Punjabi (ਪੰਜਾਬੀ)" },
];

const SEGMENTS = ["General", "VIP", "Speaker", "Sponsor", "Delegate", "Volunteer", "Press"];

interface Props {
  campaignId: string | null;
  campaignName?: string;
  initialTab?: "single" | "csv";
  onClose: () => void;
  onSuccess: (count: number) => void;
}

type Tab = "single" | "csv";
type CampaignOption = { id: string; name: string };

export default function AddContactsDrawer({
  campaignId: initialCampaignId,
  campaignName: initialCampaignName,
  initialTab = "single",
  onClose,
  onSuccess,
}: Props) {
  const [tab, setTab] = useState<Tab>(initialTab);
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [message, setMessage] = useState<string>("");
  const [dragOver, setDragOver] = useState(false);
  const [csvPreviewCount, setCsvPreviewCount] = useState<number | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const csvRef = useRef<HTMLInputElement>(null);

  // Prevent background scrolling when drawer is open
  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, []);

  // ── Campaign selector ──────────────────────────────────────────────
  const [campaigns, setCampaigns] = useState<CampaignOption[]>([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string>(initialCampaignId ?? "");
  const [campaignsLoading, setCampaignsLoading] = useState(false);
  const [campaignsError, setCampaignsError] = useState<string | null>(null);

  const activeCampaignId = initialCampaignId ?? selectedCampaignId;
  const activeCampaignName = initialCampaignId
    ? (initialCampaignName ?? "")
    : (campaigns.find((c) => c.id === selectedCampaignId)?.name ?? "");

  useEffect(() => {
    if (initialCampaignId) return;
    setCampaignsLoading(true);
    setCampaignsError(null);
    fetch(`${API}/api/v1/campaigns/?limit=50`)
      .then((r) => {
        if (!r.ok) throw new Error("Failed to load campaigns");
        return r.json();
      })
      .then((d) => setCampaigns(Array.isArray(d) ? d : (d?.items ?? d?.campaigns ?? [])))
      .catch((e) => setCampaignsError(e.message))
      .finally(() => setCampaignsLoading(false));
  }, [initialCampaignId]);

  // ── Single contact form state ──────────────────────────────────────────
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [lang, setLang] = useState("en");
  const [segment, setSegment] = useState("General");
  const [notes, setNotes] = useState("");

  const reset = () => {
    setStatus("idle");
    setMessage("");
    setName("");
    setPhone("");
    setLang("en");
    setSegment("General");
    setNotes("");
    setSelectedFile(null);
    setCsvPreviewCount(null);
  };

  // ── Submit single contact ──────────────────────────────────────────────
  const submitSingle = async () => {
    if (!phone.trim()) {
      setMessage("Phone number is required.");
      setStatus("error");
      return;
    }
    setStatus("loading");
    setMessage("");
    try {
      const res = await fetch(`${API}/api/v1/contacts/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          campaign_id: activeCampaignId || undefined,
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
      setStatus("done");
      setMessage(`✅ Contact ${name.trim() || phone.trim()} added successfully!`);
      onSuccess(1);
    } catch (e) {
      setStatus("error");
      setMessage(e instanceof Error ? e.message : "Failed to add contact");
    }
  };

  // ── Handle file selection ──────────────────────────────────────────────
  const handleFilePicked = (file: File | undefined) => {
    if (!file) return;
    setSelectedFile(file);
    setStatus("idle");
    setMessage("");

    // Estimate row count
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = (e.target?.result as string) || "";
      const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
      setCsvPreviewCount(Math.max(0, lines.length - 1));
    };
    reader.readAsText(file);
  };

  // ── Submit CSV ─────────────────────────────────────────────────────────
  const submitCsv = async () => {
    if (!selectedFile) {
      setStatus("error");
      setMessage("Please choose a CSV file to upload.");
      return;
    }
    setStatus("loading");
    setMessage("Uploading & validating contacts…");
    const form = new FormData();
    form.append("file", selectedFile);
    try {
      const endpoint = activeCampaignId
        ? `${API}/api/v1/contacts/import-to-campaign?campaign_id=${activeCampaignId}`
        : `${API}/api/v1/contacts/import`;

      const res = await fetch(endpoint, {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? `HTTP ${res.status}`);
      }
      const data = await res.json();
      const count = data.queued ?? data.imported ?? data.total ?? (csvPreviewCount || 1);
      const skipped = data.skipped ?? 0;
      setStatus("done");
      setMessage(
        `✅ Successfully imported ${count} contacts${activeCampaignName ? ` to ${activeCampaignName}` : ""}${skipped > 0 ? ` (${skipped} skipped)` : ""}!`
      );
      onSuccess(typeof count === "number" ? count : 1);
    } catch (e) {
      setStatus("error");
      setMessage(e instanceof Error ? e.message : "Import failed");
    }
  };

  // ── Sample CSV download helper ────────────────────────────────────────
  const downloadSampleCsv = () => {
    const csvContent =
      "data:text/csv;charset=utf-8," +
      "name,phone,language,segment,notes\n" +
      "Arjun Sharma,+919876543210,hi,VIP,Keynote Speaker\n" +
      "Priya Nair,+919123456789,ta,Delegate,Chennai Summit\n" +
      "Rahul Verma,+919811122233,en,Sponsor,Lead Partner\n" +
      "Anita Rao,+919444455566,te,General,RSVP confirmation\n";
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "veylo_contacts_sample.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const inputStyle: React.CSSProperties = {
    width: "100%",
    border: "1.5px solid rgba(23,38,58,.12)",
    borderRadius: 8,
    padding: "9px 13px",
    fontFamily: "Manrope, sans-serif",
    fontSize: 13,
    boxSizing: "border-box",
    outline: "none",
    color: "#17263A",
  };

  const labelStyle: React.CSSProperties = {
    display: "block",
    fontFamily: "Manrope, sans-serif",
    fontSize: 11,
    fontWeight: 700,
    color: "#8A9BB0",
    letterSpacing: ".06em",
    textTransform: "uppercase",
    marginBottom: 5,
  };

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={status === "loading" ? undefined : onClose}
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 1000,
          background: "rgba(10,16,28,.5)",
          backdropFilter: "blur(3px)",
          cursor: "pointer",
        }}
      />

      {/* Drawer */}
      <div
        style={{
          position: "fixed",
          top: 0,
          bottom: 0,
          right: 0,
          width: "min(100vw, 520px)",
          height: "100vh",
          maxHeight: "100vh",
          zIndex: 1001,
          background: "#fff",
          boxShadow: "-8px 0 40px rgba(10,16,28,.18)",
          display: "flex",
          flexDirection: "column",
          fontFamily: "Manrope, sans-serif",
          animation: "slideInRight .25s cubic-bezier(.4,0,.2,1)",
          overflow: "hidden",
        }}
      >
        <style>{`@keyframes slideInRight{from{transform:translateX(100%)}to{transform:translateX(0)}}`}</style>

        {/* Scrollable internal content */}
        <div
          style={{
            padding: "24px 28px 40px",
            flex: 1,
            overflowY: "auto",
            minHeight: 0,
            WebkitOverflowScrolling: "touch",
            overscrollBehavior: "contain",
          }}
        >
          {/* Header */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: ".1em", color: "#8A9BB0", textTransform: "uppercase", marginBottom: 3 }}>
                Audience Manager
              </div>
              <h2 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: "#17263A", letterSpacing: "-.03em" }}>
                {activeCampaignName ? `Add Contacts to ${activeCampaignName}` : "Add Contacts"}
              </h2>
            </div>
            <button
              onClick={onClose}
              style={{
                background: "rgba(23,38,58,.06)",
                border: "none",
                borderRadius: 8,
                width: 32,
                height: 32,
                cursor: "pointer",
                fontSize: 16,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#5A6E84",
              }}
            >
              ✕
            </button>
          </div>

          {/* Optional Campaign Target Selector */}
          {!initialCampaignId && (
            <div style={{ marginBottom: 18, background: "#F8FAFC", padding: "12px 14px", borderRadius: 10, border: "1px solid rgba(23,38,58,.07)" }}>
              <label style={{ ...labelStyle, marginBottom: 4 }}>
                Target Campaign <span style={{ color: "#8A9BB0", fontWeight: 400 }}>(optional — link to campaign for instant calling)</span>
              </label>
              {campaignsLoading ? (
                <div style={{ fontSize: 12, color: "#8A9BB0" }}>Loading campaigns…</div>
              ) : campaignsError ? (
                <div style={{ fontSize: 12, color: "#EA1D2C" }}>Failed to load campaigns</div>
              ) : (
                <select
                  value={selectedCampaignId}
                  onChange={(e) => setSelectedCampaignId(e.target.value)}
                  style={{ ...inputStyle, background: "#fff" }}
                >
                  <option value="">— General Audience (No specific campaign) —</option>
                  {campaigns
                    .filter((c) => c && c.name && c.name.trim().length > 0)
                    .map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                </select>
              )}
            </div>
          )}

          {/* Tabs: Individual vs Bulk CSV */}
          <div style={{ display: "flex", gap: 4, background: "#F1F5F9", borderRadius: 10, padding: 4, marginBottom: 22 }}>
            {(["single", "csv"] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => {
                  setTab(t);
                  reset();
                }}
                style={{
                  flex: 1,
                  padding: "9px 0",
                  border: "none",
                  borderRadius: 7,
                  cursor: "pointer",
                  fontFamily: "Manrope, sans-serif",
                  fontWeight: 700,
                  fontSize: 12,
                  letterSpacing: ".02em",
                  background: tab === t ? "#fff" : "transparent",
                  color: tab === t ? "#17263A" : "#8A9BB0",
                  boxShadow: tab === t ? "0 1px 4px rgba(23,38,58,.10)" : "none",
                  transition: "all .15s",
                }}
              >
                {t === "single" ? "👤 Individual Contact" : "📁 Bulk CSV Import"}
              </button>
            ))}
          </div>

          {/* ── Mode 1: Individual Contact ──────────────────────────────── */}
          {tab === "single" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div>
                  <label style={labelStyle}>Full Name</label>
                  <input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Arjun Sharma"
                    style={inputStyle}
                  />
                </div>
                <div>
                  <label style={labelStyle}>
                    Phone Number <span style={{ color: "#EA1D2C" }}>*</span>
                  </label>
                  <input
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+91 98765 43210"
                    style={inputStyle}
                    type="tel"
                  />
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div>
                  <label style={labelStyle}>Primary Language</label>
                  <select value={lang} onChange={(e) => setLang(e.target.value)} style={inputStyle}>
                    {LANGS.map((l) => (
                      <option key={l.code} value={l.code}>
                        {l.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label style={labelStyle}>Segment / Category</label>
                  <select value={segment} onChange={(e) => setSegment(e.target.value)} style={inputStyle}>
                    {SEGMENTS.map((s) => (
                      <option key={s}>{s}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label style={labelStyle}>
                  Notes & Metadata <span style={{ color: "#CBD5E1", fontWeight: 400 }}>(optional)</span>
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="e.g. Keynote speaker, prefers morning calls, TechSparks delegate"
                  rows={2}
                  style={{ ...inputStyle, resize: "vertical", minHeight: 60 }}
                />
              </div>

              {/* Status Feedback */}
              {message && (
                <div
                  style={{
                    background: status === "done" ? "#F0FDF4" : "#FFF1F2",
                    border: `1px solid ${status === "done" ? "#BBF7D0" : "#FECDD3"}`,
                    borderRadius: 8,
                    padding: "10px 14px",
                    fontSize: 12,
                    fontWeight: 600,
                    color: status === "done" ? "#15803D" : "#DC2626",
                  }}
                >
                  {message}
                </div>
              )}

              <div style={{ display: "flex", gap: 10, marginTop: 6 }}>
                {status === "done" ? (
                  <>
                    <button
                      onClick={reset}
                      style={{
                        flex: 1,
                        background: "#17263A",
                        color: "#fff",
                        border: "none",
                        borderRadius: 8,
                        padding: 11,
                        fontWeight: 700,
                        fontSize: 13,
                        cursor: "pointer",
                      }}
                    >
                      + Add Another
                    </button>
                    <button
                      onClick={onClose}
                      style={{
                        flex: 1,
                        background: "#EA1D2C",
                        color: "#fff",
                        border: "none",
                        borderRadius: 8,
                        padding: 11,
                        fontWeight: 700,
                        fontSize: 13,
                        cursor: "pointer",
                      }}
                    >
                      Done ✓
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={submitSingle}
                      disabled={status === "loading"}
                      style={{
                        flex: 1,
                        background: "#EA1D2C",
                        color: "#fff",
                        border: "none",
                        borderRadius: 8,
                        padding: 11,
                        fontWeight: 700,
                        fontSize: 13,
                        cursor: status === "loading" ? "not-allowed" : "pointer",
                        opacity: status === "loading" ? 0.7 : 1,
                      }}
                    >
                      {status === "loading" ? "Adding…" : "Add Contact"}
                    </button>
                    <button
                      onClick={onClose}
                      style={{
                        padding: "11px 18px",
                        background: "transparent",
                        border: "1.5px solid rgba(23,38,58,.12)",
                        borderRadius: 8,
                        fontWeight: 700,
                        fontSize: 13,
                        cursor: "pointer",
                      }}
                    >
                      Cancel
                    </button>
                  </>
                )}
              </div>
            </div>
          )}

          {/* ── Mode 2: Bulk CSV Import ─────────────────────────────────── */}
          {tab === "csv" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {/* Drop zone */}
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragOver(false);
                  handleFilePicked(e.dataTransfer.files[0]);
                }}
                onClick={() => csvRef.current?.click()}
                style={{
                  border: `2px dashed ${dragOver ? "#EA1D2C" : selectedFile ? "#10B981" : "rgba(23,38,58,.15)"}`,
                  borderRadius: 12,
                  padding: "30px 20px",
                  textAlign: "center",
                  cursor: "pointer",
                  transition: "all .15s",
                  background: dragOver ? "#FFF1F2" : selectedFile ? "#F0FDF4" : "#FAFBFC",
                }}
              >
                <div style={{ fontSize: 32, marginBottom: 8 }}>{selectedFile ? "📄" : "📁"}</div>
                <p style={{ margin: "0 0 4px", fontWeight: 700, fontSize: 14, color: "#17263A" }}>
                  {selectedFile
                    ? `${selectedFile.name} (${csvPreviewCount ?? "?"} contacts detected)`
                    : "Drop your CSV here or click to browse"}
                </p>
                <p style={{ margin: 0, fontSize: 11, color: "#8A9BB0" }}>
                  Supports standard comma-separated contacts (.csv)
                </p>
                <input
                  ref={csvRef}
                  type="file"
                  accept=".csv"
                  style={{ display: "none" }}
                  onChange={(e) => handleFilePicked(e.target.files?.[0])}
                />
              </div>

              {/* Template & Format Helper */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "#F8FAFC", padding: "10px 14px", borderRadius: 8, border: "1px solid rgba(23,38,58,.08)" }}>
                <div style={{ fontSize: 11, color: "#5A6E84" }}>
                  Columns: <strong>name, phone, language, segment, notes</strong>
                </div>
                <button
                  type="button"
                  onClick={downloadSampleCsv}
                  style={{
                    background: "#fff",
                    border: "1px solid rgba(23,38,58,.15)",
                    borderRadius: 6,
                    padding: "4px 10px",
                    fontSize: 11,
                    fontWeight: 700,
                    color: "#EA1D2C",
                    cursor: "pointer",
                  }}
                >
                  ⬇ Download Sample CSV
                </button>
              </div>

              {/* Status Message */}
              {message && (
                <div
                  style={{
                    background: status === "done" ? "#F0FDF4" : "#FFF1F2",
                    border: `1px solid ${status === "done" ? "#BBF7D0" : "#FECDD3"}`,
                    borderRadius: 8,
                    padding: "12px 16px",
                    fontSize: 13,
                    fontWeight: 600,
                    color: status === "done" ? "#15803D" : "#DC2626",
                  }}
                >
                  {message}
                </div>
              )}

              {/* Action Buttons */}
              <div style={{ display: "flex", gap: 10 }}>
                {status === "done" ? (
                  <button
                    onClick={onClose}
                    style={{
                      width: "100%",
                      background: "#EA1D2C",
                      color: "#fff",
                      border: "none",
                      borderRadius: 8,
                      padding: 12,
                      fontWeight: 700,
                      fontSize: 14,
                      cursor: "pointer",
                    }}
                  >
                    Done ✓
                  </button>
                ) : (
                  <>
                    <button
                      onClick={submitCsv}
                      disabled={status === "loading" || !selectedFile}
                      style={{
                        flex: 1,
                        background: "#EA1D2C",
                        color: "#fff",
                        border: "none",
                        borderRadius: 8,
                        padding: 11,
                        fontWeight: 700,
                        fontSize: 13,
                        cursor: status === "loading" || !selectedFile ? "not-allowed" : "pointer",
                        opacity: status === "loading" || !selectedFile ? 0.6 : 1,
                      }}
                    >
                      {status === "loading" ? "Importing…" : "Upload & Save Contacts"}
                    </button>
                    <button
                      onClick={onClose}
                      style={{
                        padding: "11px 18px",
                        background: "transparent",
                        border: "1.5px solid rgba(23,38,58,.12)",
                        borderRadius: 8,
                        fontWeight: 700,
                        fontSize: 13,
                        cursor: "pointer",
                      }}
                    >
                      Cancel
                    </button>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
