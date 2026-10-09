"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PageHeader from "@/components/ui/PageHeader";
import { campaignsApi, templatesApi } from "@/lib/api-client";
import type { Template } from "@/types";

// ── Types ────────────────────────────────────────────────────────────────────

interface WizardState {
  campaignName: string;
  eventName: string;
  eventDate: string;
  city: string;
  templateId: string;
  languages: string[];
  contactsFile: File | null;
}

const EMPTY: WizardState = {
  campaignName: "",
  eventName: "",
  eventDate: "",
  city: "",
  templateId: "",
  languages: [],
  contactsFile: null,
};

const STEPS = ["Event", "Contacts", "Language", "Template", "Review"];

const LANGUAGE_OPTIONS = [
  { value: "en", label: "English" },
  { value: "ml", label: "Malayalam" },
  { value: "hi", label: "Hindi" },
  { value: "ta", label: "Tamil" },
  { value: "fr", label: "French" },
  { value: "es", label: "Spanish" },
  { value: "ar", label: "Arabic" },
];

const REQUIRED_CSV_HEADERS = [
  "phone",
  "name",
  "language",
  "segment",
  "consent",
  "dnd",
];

// ── Component ─────────────────────────────────────────────────────────────────

export default function NewCampaignPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [state, setState] = useState<WizardState>(EMPTY);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [csvPreviewHeaders, setCsvPreviewHeaders] = useState<string[]>([]);
  const [csvError, setCsvError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  // Load templates for step 4.
  useEffect(() => {
    templatesApi
      .list()
      .catch(() => [] as Template[])
      .then(setTemplates);
  }, []);

  const update = (partial: Partial<WizardState>) =>
    setState((prev) => ({ ...prev, ...partial }));

  // ── Validation ──────────────────────────────────────────────────────────────

  const validateCurrent = (): string | null => {
    switch (step) {
      case 0:
        if (!state.campaignName.trim()) return "Campaign name is required.";
        if (!state.eventDate) return "Event date is required.";
        return null;
      case 1:
        if (!state.contactsFile) return "Please select a contacts CSV file.";
        if (csvError) return csvError;
        return null;
      case 2:
        if (!state.languages.length) return "Select at least one language.";
        return null;
      case 3:
        if (!state.templateId) return "Select a template.";
        return null;
      default:
        return null;
    }
  };

  const goNext = () => {
    const err = validateCurrent();
    if (err) { setError(err); return; }
    setError(null);
    setStep((s) => Math.min(s + 1, STEPS.length - 1));
  };

  const goBack = () => {
    setError(null);
    setStep((s) => Math.max(s - 1, 0));
  };

  // ── CSV preview ─────────────────────────────────────────────────────────────

  const handleFileChange = (file: File | null) => {
    setCsvError(null);
    setCsvPreviewHeaders([]);
    if (!file) { update({ contactsFile: null }); return; }
    update({ contactsFile: file });
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const firstLine = text.split(/\r?\n/)[0] ?? "";
      const headers = firstLine.split(",").map((h) => h.trim().toLowerCase());
      setCsvPreviewHeaders(headers);
      const missing = REQUIRED_CSV_HEADERS.filter((h) => !headers.includes(h));
      if (missing.length) {
        setCsvError(`CSV is missing required columns: ${missing.join(", ")}`);
      }
    };
    reader.readAsText(file);
  };

  // ── Language toggle ──────────────────────────────────────────────────────────

  const toggleLanguage = (lang: string) =>
    update({
      languages: state.languages.includes(lang)
        ? state.languages.filter((l) => l !== lang)
        : [...state.languages, lang],
    });

  // ── Submit ───────────────────────────────────────────────────────────────────

  const submit = async () => {
    setError(null);
    setLoading(true);
    try {
      // 1. Create campaign — body per CONTRACTS.md §6:
      // { name, template_id, event_details, languages[] }
      // event_details is a JSON object of template variable values.
      setStatusMsg("Creating campaign…");
      const campaign = await campaignsApi.create({
        name: state.campaignName,
        template_id: state.templateId,
        languages: state.languages,
        event_details: {
          event_name: state.eventName || state.campaignName,
          date: state.eventDate,
          venue: state.city,
        },
      } as any);

      // 2. Upload contacts CSV
      if (state.contactsFile) {
        setStatusMsg("Uploading contacts CSV…");
        await campaignsApi.importContacts(campaign.id, state.contactsFile);
      }

      // 3. Prepare (trigger translation + audio)
      setStatusMsg("Preparing campaign…");
      await campaignsApi.prepare(campaign.id);

      // 4. Poll GET /api/campaigns/{id} for readiness (max 60 s)
      setStatusMsg("Waiting for campaign to become ready…");
      const maxAttempts = 20;
      let ready = false;
      for (let i = 0; i < maxAttempts; i++) {
        await new Promise((r) => setTimeout(r, 3000));
        const detail = await campaignsApi.get(campaign.id);
        // Contract §6: readiness object has can_launch (bool).
        // Campaign status "ready" also means it can be launched.
        const r = (detail as any).readiness;
        if (detail.status === "ready" || r?.can_launch === true) {
          ready = true;
          break;
        }
      }

      if (!ready) {
        setError(
          "Campaign preparation timed out. You can launch manually from the campaign detail page."
        );
        setLoading(false);
        return;
      }

      // 5. Launch
      setStatusMsg("Launching campaign…");
      await campaignsApi.launch(campaign.id);

      setStatusMsg("Campaign launched successfully! Redirecting…");
      setDone(true);
      setTimeout(() => router.push(`/campaigns/${campaign.id}`), 1500);
    } catch (e: unknown) {
      setError(
        `Error: ${e instanceof Error ? e.message : String(e)}`
      );
    } finally {
      setLoading(false);
    }
  };

  // ── Render ───────────────────────────────────────────────────────────────────

  const renderStep = () => {
    switch (step) {
      // ── Step 0: Event details ───────────────────────────────────────────────
      case 0:
        return (
          <div className="glass" style={{ padding: "18px 20px", maxWidth: 600 }}>
            <label style={{ display: "block", font: "700 12px 'Manrope'", marginBottom: 14 }}>
              Campaign name *
              <input
                className="vfield"
                placeholder="e.g. Onam Cultural Night 2026"
                value={state.campaignName}
                onChange={(e) => update({ campaignName: e.target.value })}
                style={{ marginTop: 5, fontWeight: 400 }}
              />
            </label>
            <label style={{ display: "block", font: "700 12px 'Manrope'", marginBottom: 14 }}>
              Event name
              <input
                className="vfield"
                placeholder="e.g. Onam Cultural Night"
                value={state.eventName}
                onChange={(e) => update({ eventName: e.target.value })}
                style={{ marginTop: 5, fontWeight: 400 }}
              />
            </label>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <label style={{ flex: "1 1 180px", font: "700 12px 'Manrope'", marginBottom: 14 }}>
                Event date *
                <input
                  type="date"
                  className="vfield"
                  value={state.eventDate}
                  onChange={(e) => update({ eventDate: e.target.value })}
                  style={{ marginTop: 5, fontWeight: 400 }}
                />
              </label>
              <label style={{ flex: "1 1 180px", font: "700 12px 'Manrope'", marginBottom: 14 }}>
                City or venue
                <input
                  className="vfield"
                  placeholder="e.g. Kochi"
                  value={state.city}
                  onChange={(e) => update({ city: e.target.value })}
                  style={{ marginTop: 5, fontWeight: 400 }}
                />
              </label>
            </div>
          </div>
        );

      // ── Step 1: Contacts CSV ────────────────────────────────────────────────
      case 1:
        return (
          <div className="glass" style={{ padding: "18px 20px", maxWidth: 600 }}>
            <p style={{ font: "700 12px 'Manrope'", marginBottom: 10 }}>
              Upload contacts CSV *
            </p>
            <p style={{ font: "400 11px 'Manrope'", color: "#5B6B7D", marginBottom: 14 }}>
              Required columns: <code>{REQUIRED_CSV_HEADERS.join(", ")}</code>
            </p>
            <input
              ref={fileRef}
              type="file"
              accept=".csv,text/csv"
              style={{ display: "none" }}
              onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
            />
            <button
              className="vbtn"
              type="button"
              onClick={() => fileRef.current?.click()}
            >
              {state.contactsFile ? "Change file" : "Choose CSV file"}
            </button>
            {state.contactsFile && (
              <p style={{ marginTop: 10, font: "600 12px 'Manrope'" }}>
                ✓ {state.contactsFile.name}
              </p>
            )}
            {csvPreviewHeaders.length > 0 && (
              <p style={{ marginTop: 6, font: "400 11px 'Manrope'", color: "#5B6B7D" }}>
                Detected headers: {csvPreviewHeaders.join(", ")}
              </p>
            )}
            {csvError && (
              <p style={{ color: "var(--red)", font: "600 11px 'Manrope'", marginTop: 6 }}>
                {csvError}
              </p>
            )}
          </div>
        );

      // ── Step 2: Language selection ──────────────────────────────────────────
      case 2:
        return (
          <div className="glass" style={{ padding: "18px 20px", maxWidth: 600 }}>
            <p style={{ font: "700 12px 'Manrope'", marginBottom: 14 }}>
              Select call languages * (choose all that apply)
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {LANGUAGE_OPTIONS.map(({ value, label }) => {
                const active = state.languages.includes(value);
                return (
                  <button
                    key={value}
                    type="button"
                    className="vbtn vbtn-sm"
                    onClick={() => toggleLanguage(value)}
                    style={{
                      background: active ? "var(--ink)" : "var(--white)",
                      color: active ? "var(--white)" : "var(--ink)",
                      border: "1.5px solid var(--ink)",
                    }}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
            {state.languages.length > 0 && (
              <p style={{ marginTop: 12, font: "600 11px 'Manrope'", color: "#5B6B7D" }}>
                Selected: {state.languages.join(", ")}
              </p>
            )}
          </div>
        );

      // ── Step 3: Template selection ──────────────────────────────────────────
      case 3:
        return (
          <div className="glass" style={{ padding: "18px 20px", maxWidth: 600 }}>
            <p style={{ font: "700 12px 'Manrope'", marginBottom: 14 }}>
              Select a call template *
            </p>
            {templates.length === 0 ? (
              <p style={{ font: "400 12px 'Manrope'", color: "#5B6B7D" }}>
                Loading templates…
              </p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {templates.map((t) => {
                  const active = state.templateId === t.id;
                  return (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => update({ templateId: t.id })}
                      style={{
                        textAlign: "left",
                        padding: "10px 14px",
                        border: active
                          ? "2px solid var(--ink)"
                          : "1.5px solid rgba(0,0,0,.12)",
                        borderRadius: 6,
                        background: active ? "var(--ink)" : "transparent",
                        color: active ? "var(--white)" : "inherit",
                        cursor: "pointer",
                        font: "600 13px 'Manrope'",
                      }}
                    >
                      {t.name}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        );

      // ── Step 4: Review & launch ─────────────────────────────────────────────
      case 4:
        return (
          <div className="glass" style={{ padding: "18px 20px", maxWidth: 600 }}>
            <h3 style={{ font: "800 16px 'Manrope'", marginBottom: 16 }}>
              Review before launch
            </h3>
            {[
              ["Campaign name", state.campaignName],
              ["Event name", state.eventName || "—"],
              ["Event date", state.eventDate],
              ["City", state.city || "—"],
              ["Languages", state.languages.join(", ") || "—"],
              [
                "Template",
                templates.find((t) => t.id === state.templateId)?.name ?? state.templateId,
              ],
              [
                "Contacts file",
                state.contactsFile ? state.contactsFile.name : "none",
              ],
            ].map(([label, value]) => (
              <div
                key={label}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  padding: "6px 0",
                  borderBottom: "1px solid rgba(0,0,0,.06)",
                  font: "400 13px 'Manrope'",
                }}
              >
                <span style={{ fontWeight: 700 }}>{label}</span>
                <span style={{ color: "#4A5B6E" }}>{value}</span>
              </div>
            ))}

            {statusMsg && (
              <p
                style={{
                  marginTop: 16,
                  font: "600 13px 'Manrope'",
                  color: done ? "green" : "var(--ink)",
                }}
              >
                {statusMsg}
              </p>
            )}

            {!done && (
              <button
                className="vbtn vbtn-red"
                style={{ marginTop: 18 }}
                onClick={submit}
                disabled={loading}
              >
                {loading ? "Processing…" : "CREATE & LAUNCH ↗"}
              </button>
            )}
          </div>
        );
    }
  };

  return (
    <div className="page-in" style={{ maxWidth: 1180, margin: "0 auto", padding: "30px 28px 60px" }}>
      <PageHeader
        eyebrow="create campaign"
        title="Create campaign"
        subtitle="Five short steps. Your progress is saved as you go."
        tagline="Begin the invitation."
        bubble="Let's build one!"
        mascot="boy"
      />

      {/* Step bar */}
      <div className="wz" style={{ marginBottom: 24 }}>
        {STEPS.map((s, i) => (
          <div key={s} className={`wz-step ${i === step ? "active" : i < step ? "done" : ""}`}>
            {i + 1}<span style={{ marginLeft: 4 }}>{s}</span>
          </div>
        ))}
      </div>

      {/* Error banner */}
      {error && (
        <p
          style={{
            color: "var(--red)",
            font: "600 13px 'Manrope'",
            marginBottom: 12,
            padding: "8px 12px",
            background: "rgba(220,50,50,.08)",
            borderRadius: 6,
            maxWidth: 600,
          }}
        >
          {error}
        </p>
      )}

      {/* Step content */}
      {renderStep()}

      {/* Navigation */}
      <div style={{ display: "flex", gap: 10, marginTop: 18 }}>
        {step === 0 ? (
          <Link href="/campaigns" className="vbtn" style={{ textDecoration: "none", opacity: 0.45 }}>
            ← BACK
          </Link>
        ) : (
          <button className="vbtn" onClick={goBack} disabled={loading} style={{ opacity: 0.45 }}>
            ← BACK
          </button>
        )}
        {step < STEPS.length - 1 && (
          <button className="vbtn vbtn-ink" onClick={goNext} disabled={loading}>
            NEXT →
          </button>
        )}
      </div>

      <div className="pgf"><span>VEYLO / CREATE CAMPAIGN</span><i>✳</i></div>
    </div>
  );
}
