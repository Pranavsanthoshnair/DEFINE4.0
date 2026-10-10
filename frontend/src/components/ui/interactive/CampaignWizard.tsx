"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const STEPS = ["Event & Host Details", "Audience & Languages", "Indic Voice & Script", "Launch & Schedule"] as const;

const REQUIRED_CSV_HEADERS = ["phone"];

const INDIC_VOICES = [
  { id: "sarvam-hi-female", name: "Sarvam — Hindi Natural (Female)", lang: "hi", provider: "Sarvam AI" },
  { id: "elevenlabs-multilingual", name: "ElevenLabs — Multilingual Indic (Natural)", lang: "multi", provider: "ElevenLabs" },
  { id: "sarvam-ta-female", name: "Sarvam — Tamil Conversational", lang: "ta", provider: "Sarvam AI" },
  { id: "sarvam-te-male", name: "Sarvam — Telugu Expressive", lang: "te", provider: "Sarvam AI" },
  { id: "google-indic-wavenet", name: "Google WaveNet — High Fidelity Indic", lang: "multi", provider: "Google" },
];

export default function CampaignWizard() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitStatus, setSubmitStatus] = useState<string | null>(null);
  const [csvError, setCsvError] = useState<string | null>(null);
  const [recipientFile, setRecipientFile] = useState<File | null>(null);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // Form State
  const [formData, setFormData] = useState({
    title: "",
    orgName: "",
    eventType: "VIP Invitation",
    date: "",
    time: "",
    venue: "",
    rsvpDeadline: "",
    recipientsFile: "",
    recipientCount: 0,
    primaryLanguage: "hi",
    secondaryLanguage: "en",
    templateType: "Event Invitation",
    scriptText: "Namaskar {name}, on behalf of {organization}, you are cordially invited to attend {event_name}. Please confirm your attendance.",
    voice: "Sarvam — Hindi Natural (Female)",
    maxRetries: "2",
    concurrency: "3",
    scheduledAt: "",
  });

  const updateField = (key: string, value: any) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
    if (validationErrors[key]) {
      setValidationErrors((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
    }
  };

  const handleFileSelect = (file: File | null) => {
    setCsvError(null);
    if (validationErrors.recipientsFile) {
      setValidationErrors((prev) => {
        const next = { ...prev };
        delete next.recipientsFile;
        return next;
      });
    }
    setRecipientFile(file);
    if (!file) {
      updateField("recipientsFile", "");
      updateField("recipientCount", 0);
      return;
    }
    updateField("recipientsFile", file.name);
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = (e.target?.result as string) || "";
      const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
      const firstLine = lines[0] ?? "";
      const headers = firstLine.split(",").map((h) => h.trim().toLowerCase());
      const missing = REQUIRED_CSV_HEADERS.filter((h) => !headers.includes(h));
      if (missing.length) {
        setCsvError(`CSV must include at least a "phone" column. Detected: ${headers.join(", ")}`);
      }
      const rows = Math.max(0, lines.length - 1);
      updateField("recipientCount", rows);
    };
    reader.readAsText(file);
  };

  const validateStep = (step: number) => {
    const errors: Record<string, string> = {};
    if (step === 0) {
      if (!formData.title.trim()) {
        errors.title = "Please enter a Campaign Title (e.g. Annual Tech Summit 2026)";
      }
    }
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // ── Handle Submit & Launch ────────────────────────────────────────────────
  const handleLaunch = async () => {
    setSubmitError(null);
    setIsSubmitting(true);
    setSubmitStatus("Creating campaign…");

    try {
      // 1. Create campaign in backend
      const res = await fetch(`${API}/api/v1/campaigns/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: formData.title.trim() || "Untitled Campaign",
          org_name: formData.orgName.trim() || undefined,
          organization: formData.orgName.trim() || undefined,
          description: formData.orgName.trim() ? `Host: ${formData.orgName.trim()}` : undefined,
          language: formData.primaryLanguage,
          languages: [formData.primaryLanguage, formData.secondaryLanguage],
          brief: formData.scriptText.trim(),
          status: "draft",
          max_retries: parseInt(formData.maxRetries, 10) || 2,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail || `HTTP ${res.status}`);
      }

      const campaign = await res.json();
      const campaignId = campaign.id;

      // 2. Upload contacts CSV if provided
      if (recipientFile) {
        setSubmitStatus("Uploading audience contacts…");
        const form = new FormData();
        form.append("file", recipientFile);
        await fetch(`${API}/api/v1/contacts/import-to-campaign?campaign_id=${campaignId}`, {
          method: "POST",
          body: form,
        }).catch((e) => console.warn("CSV upload note:", e));
      }

      setSubmitStatus("Campaign created successfully! Opening campaign dashboard…");
      setTimeout(() => {
        router.push(`/campaigns/${campaignId}`);
      }, 600);
    } catch (e: unknown) {
      setSubmitError(e instanceof Error ? e.message : "Failed to create campaign");
      setIsSubmitting(false);
    }
  };

  const handleNext = () => {
    if (!validateStep(currentStep)) return;
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleLaunch();
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-12">
      {/* Stepper Header */}
      <div className="grid grid-cols-4 gap-2 border-b border-stone-200 pb-6">
        {STEPS.map((step, idx) => {
          const isDone = idx < currentStep;
          const isCurrent = idx === currentStep;
          return (
            <div
              key={step}
              onClick={() => idx <= currentStep && setCurrentStep(idx)}
              className={`flex items-center gap-3 transition-transform ${idx <= currentStep ? "cursor-pointer hover:opacity-90" : "opacity-60"}`}
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-mono font-bold transition-all ${
                  isCurrent
                    ? "bg-[#EA1D2C] text-white ring-4 ring-red-100 shadow-md scale-105"
                    : isDone
                    ? "bg-[#17263A] text-white shadow-xs"
                    : "bg-stone-100 text-stone-600 border border-stone-200"
                }`}
              >
                {isDone ? "✓" : idx + 1}
              </div>
              <div className="hidden sm:block">
                <div className="text-[10px] uppercase font-mono text-stone-400">Step 0{idx + 1}</div>
                <div className={`text-xs font-medium ${isCurrent ? "text-stone-900 font-bold" : "text-stone-500"}`}>
                  {step}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Step Container */}
      <div className="bg-white rounded-2xl border border-stone-200 p-6 sm:p-8 shadow-sm font-sans">
        {/* ── STEP 0: Event & Host Details ──────────────────────────── */}
        {currentStep === 0 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-bold text-[#17263A]">Event & Host Details</h2>
              <p className="text-xs text-stone-500 mt-1">Specify campaign parameters to personalize your outbound voice outreach.</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold uppercase text-[#8A9BB0] tracking-wider mb-1.5">
                  Campaign Title <span className="text-[#EA1D2C]">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g., Annual Tech Summit VIP Invitation"
                  value={formData.title}
                  onChange={(e) => updateField("title", e.target.value)}
                  className={`w-full px-3.5 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-[#EA1D2C] ${validationErrors.title ? "border-red-400 bg-red-50/20" : "border-stone-300"}`}
                />
                {validationErrors.title && (
                  <p className="text-[11px] text-[#DC2626] font-medium mt-1">{validationErrors.title}</p>
                )}
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-[#8A9BB0] tracking-wider mb-1.5">
                  Host Organization / Client Name
                </label>
                <input
                  type="text"
                  placeholder="e.g., YourStory Media / DEFINE Labs"
                  value={formData.orgName}
                  onChange={(e) => updateField("orgName", e.target.value)}
                  className="w-full px-3.5 py-2.5 text-sm border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-[#EA1D2C]"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-[#8A9BB0] tracking-wider mb-1.5">Event Type</label>
                <select
                  value={formData.eventType}
                  onChange={(e) => updateField("eventType", e.target.value)}
                  className="w-full px-3.5 py-2.5 text-sm border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-[#EA1D2C] bg-white"
                >
                  <option>VIP Invitation</option>
                  <option>Keynote Confirmation</option>
                  <option>RSVP Reminder</option>
                  <option>Delegate Update</option>
                  <option>Feedback Survey</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-[#8A9BB0] tracking-wider mb-1.5">
                  Venue / Location <span className="text-stone-400 font-normal">(optional)</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g., Grand Ballroom, Mumbai / Virtual"
                  value={formData.venue}
                  onChange={(e) => updateField("venue", e.target.value)}
                  className="w-full px-3.5 py-2.5 text-sm border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-[#EA1D2C]"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-[#8A9BB0] tracking-wider mb-1.5">
                  Event Date <span className="text-stone-400 font-normal">(optional)</span>
                </label>
                <input
                  type="date"
                  value={formData.date}
                  onChange={(e) => updateField("date", e.target.value)}
                  className="w-full px-3.5 py-2.5 text-sm border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-[#EA1D2C]"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-[#8A9BB0] tracking-wider mb-1.5">
                  Event Time <span className="text-stone-400 font-normal">(optional)</span>
                </label>
                <input
                  type="time"
                  value={formData.time}
                  onChange={(e) => updateField("time", e.target.value)}
                  className="w-full px-3.5 py-2.5 text-sm border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-[#EA1D2C]"
                />
              </div>
            </div>
          </div>
        )}

        {/* ── STEP 1: Audience & Languages ──────────────────────────── */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-bold text-[#17263A]">Audience & Language Targeting</h2>
              <p className="text-xs text-stone-500 mt-1">Upload recipient contact numbers or attach existing audience groups.</p>
            </div>

            {/* CSV Drop Zone */}
            <div className="border-2 border-dashed border-stone-300 rounded-xl p-6 text-center bg-stone-50/50 hover:bg-stone-50 transition-colors">
              <input
                type="file"
                accept=".csv"
                id="csv-upload"
                onChange={(e) => handleFileSelect(e.target.files?.[0] || null)}
                className="hidden"
              />
              <label htmlFor="csv-upload" className="cursor-pointer block">
                <div className="text-3xl mb-2">{recipientFile ? "📄" : "📁"}</div>
                <div className="text-sm font-bold text-[#17263A]">
                  {recipientFile ? recipientFile.name : "Click to select or drop CSV contact list"}
                </div>
                <div className="text-xs text-stone-400 mt-1">
                  {recipientFile ? `~${formData.recipientCount} rows detected` : "Required header: phone | Optional: name, language, segment"}
                </div>
              </label>
            </div>

            {csvError && (
              <p className="text-xs text-[#DC2626] font-medium bg-red-50 p-2.5 rounded-lg border border-red-200">
                {csvError}
              </p>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
              <div>
                <label className="block text-xs font-bold uppercase text-[#8A9BB0] tracking-wider mb-1.5">Primary Language</label>
                <select
                  value={formData.primaryLanguage}
                  onChange={(e) => updateField("primaryLanguage", e.target.value)}
                  className="w-full px-3.5 py-2.5 text-sm border border-stone-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-[#EA1D2C]"
                >
                  <option value="hi">Hindi (हिंदी)</option>
                  <option value="en">English</option>
                  <option value="ta">Tamil (தமிழ்)</option>
                  <option value="te">Telugu (తెలుగు)</option>
                  <option value="kn">Kannada (ಕನ್ನಡ)</option>
                  <option value="ml">Malayalam (മലയാളം)</option>
                  <option value="mr">Marathi (मराठी)</option>
                  <option value="bn">Bengali (বাংলা)</option>
                  <option value="gu">Gujarati (ગુજરાતી)</option>
                  <option value="pa">Punjabi (ਪੰਜਾਬੀ)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-[#8A9BB0] tracking-wider mb-1.5">Fallback Language</label>
                <select
                  value={formData.secondaryLanguage}
                  onChange={(e) => updateField("secondaryLanguage", e.target.value)}
                  className="w-full px-3.5 py-2.5 text-sm border border-stone-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-[#EA1D2C]"
                >
                  <option value="en">English</option>
                  <option value="hi">Hindi (हिंदी)</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* ── STEP 2: Indic Voice & Script ──────────────────────────── */}
        {currentStep === 2 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-bold text-[#17263A]">Indic Voice Model & Script Prompt</h2>
              <p className="text-xs text-stone-500 mt-1">Configure the conversational AI voice and speech template.</p>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase text-[#8A9BB0] tracking-wider mb-1.5">Voice Synthesis Profile</label>
              <select
                value={formData.voice}
                onChange={(e) => updateField("voice", e.target.value)}
                className="w-full px-3.5 py-2.5 text-sm border border-stone-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-[#EA1D2C]"
              >
                {INDIC_VOICES.map((v) => (
                  <option key={v.id} value={v.name}>
                    {v.name} ({v.provider})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase text-[#8A9BB0] tracking-wider mb-1.5">
                Spoken Script Template (supports <code className="text-[#EA1D2C] font-mono">{"{name}"}</code> and <code className="text-[#EA1D2C] font-mono">{"{organization}"}</code>)
              </label>
              <textarea
                value={formData.scriptText}
                onChange={(e) => updateField("scriptText", e.target.value)}
                rows={4}
                className="w-full px-3.5 py-2.5 text-sm border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-[#EA1D2C] font-sans"
              />
            </div>
          </div>
        )}

        {/* ── STEP 3: Launch & Schedule ─────────────────────────────── */}
        {currentStep === 3 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-bold text-[#17263A]">Dispatch Policy & Carrier Setup</h2>
              <p className="text-xs text-stone-500 mt-1">Review your deployment parameters and launch live calling.</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold uppercase text-[#8A9BB0] tracking-wider mb-1.5">Max Parallel Channels</label>
                <select
                  value={formData.concurrency}
                  onChange={(e) => updateField("concurrency", e.target.value)}
                  className="w-full px-3.5 py-2.5 text-sm border border-stone-300 rounded-lg bg-white"
                >
                  <option value="1">1 channel (Sequential)</option>
                  <option value="3">3 channels (Standard Exotel Concurrency)</option>
                  <option value="5">5 channels (High Throughput)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-[#8A9BB0] tracking-wider mb-1.5">Max Retries on No Answer</label>
                <select
                  value={formData.maxRetries}
                  onChange={(e) => updateField("maxRetries", e.target.value)}
                  className="w-full px-3.5 py-2.5 text-sm border border-stone-300 rounded-lg bg-white"
                >
                  <option value="0">No retry</option>
                  <option value="1">1 retry</option>
                  <option value="2">2 retries (Recommended)</option>
                  <option value="3">3 retries</option>
                </select>
              </div>
            </div>

            {/* Dispatch Summary Box */}
            <div className="p-4 rounded-xl bg-[#17263A] text-white space-y-3 font-sans text-xs">
              <div className="text-[11px] uppercase tracking-wider text-stone-400 font-bold border-b border-stone-700 pb-2">
                Launch Overview
              </div>
              <div className="grid grid-cols-2 gap-y-2 text-stone-300">
                <div>Campaign: <span className="text-white font-bold">{formData.title || "Untitled Campaign"}</span></div>
                <div>Host: <span className="text-white font-bold">{formData.orgName || "Veylo Demo"}</span></div>
                <div>Primary Language: <span className="text-white font-bold">{formData.primaryLanguage.toUpperCase()}</span></div>
                <div>Telephony: <span className="text-emerald-400 font-bold">Exotel Active 🟢</span></div>
              </div>
            </div>

            {submitStatus && (
              <p className="text-xs text-stone-700 bg-stone-50 border border-stone-200 px-3 py-2 rounded-lg">
                {submitStatus}
              </p>
            )}
            {submitError && (
              <p className="text-xs text-[#DC2626] bg-red-50 border border-red-200 px-3 py-2 rounded-lg font-medium">
                {submitError}
              </p>
            )}
          </div>
        )}

        {/* Wizard Navigation Footer */}
        <div className="flex items-center justify-between pt-6 border-t border-stone-200 mt-8">
          <button
            type="button"
            onClick={handleBack}
            disabled={currentStep === 0 || isSubmitting}
            className={`px-5 py-2 text-sm font-semibold rounded-lg transition-all ${
              currentStep === 0
                ? "text-stone-400 bg-stone-50 cursor-not-allowed opacity-50"
                : "text-stone-700 border border-stone-300 hover:bg-stone-100"
            }`}
          >
            ← Back
          </button>

          <button
            type="button"
            onClick={handleNext}
            disabled={isSubmitting}
            style={{
              background: "#EA1D2C",
              color: "#fff",
              padding: "10px 24px",
              borderRadius: 8,
              fontWeight: 700,
              fontSize: 13,
              cursor: isSubmitting ? "wait" : "pointer",
              boxShadow: "0 2px 8px rgba(234,29,44,.25)",
            }}
          >
            {isSubmitting ? (
              <span>Creating…</span>
            ) : currentStep === STEPS.length - 1 ? (
              <span>Launch Campaign 🚀</span>
            ) : (
              <span>Next Step →</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}