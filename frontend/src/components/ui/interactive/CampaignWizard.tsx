"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { campaignsApi } from "@/lib/api-client";

const STEPS = ["Event Details", "Recipients", "Message Script", "Launch & Schedule"] as const;

const REQUIRED_CSV_HEADERS = ["phone", "name", "language", "segment", "consent", "dnd"];

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
    eventType: "Invitation",
    date: "",
    time: "",
    venue: "",
    rsvpDeadline: "",
    recipientsFile: "",
    recipientCount: 0,
    primaryLanguage: "Hindi",
    secondaryLanguage: "English",
    templateType: "Event Invitation (Hindi)",
    scriptText: "Namaskar {name}, aapko {event_name} mein aamantrit kiya jata hai...",
    voice: "Sarvam - Hindi Natural (Female)",
    maxRetries: "2",
    concurrency: "5",
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
    // Read headers to validate required columns
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const firstLine = text.split(/\r?\n/)[0] ?? "";
      const headers = firstLine.split(",").map((h) => h.trim().toLowerCase());
      const missing = REQUIRED_CSV_HEADERS.filter((h) => !headers.includes(h));
      if (missing.length) {
        setCsvError(`CSV is missing required columns: ${missing.join(", ")}`);
      }
      // Estimate row count (lines - header)
      const rows = text.split(/\r?\n/).filter((l) => l.trim()).length - 1;
      updateField("recipientCount", Math.max(0, rows));
    };
    reader.readAsText(file);
  };

  const validateStep = (step: number) => {
    const errors: Record<string, string> = {};
    if (step === 0) {
      if (!formData.title.trim()) errors.title = "Campaign title is required";
      if (!formData.eventType) errors.eventType = "Event type is required";
      if (!formData.date) errors.date = "Date is required";
      if (!formData.time) errors.time = "Time is required";
      if (!formData.venue.trim()) errors.venue = "Venue is required";
    } else if (step === 1) {
      if (!recipientFile && !formData.recipientsFile) errors.recipientsFile = "Please upload a recipients CSV file";
      if (!formData.primaryLanguage) errors.primaryLanguage = "Primary language is required";
    } else if (step === 2) {
      if (!formData.voice) errors.voice = "Voice engine profile is required";
      if (!formData.scriptText.trim()) errors.scriptText = "Voice script is required";
    } else if (step === 3) {
      if (!formData.concurrency) errors.concurrency = "Concurrency is required";
      if (!formData.maxRetries) errors.maxRetries = "Max retries is required";
    }
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // ── Submit (real API — CONTRACTS.md §6) ───────────────────────────────────

  const handleLaunch = async () => {
    setSubmitError(null);
    setIsSubmitting(true);
    try {
      // 1. Create campaign
      setSubmitStatus("Creating campaign…");
      const campaign = await campaignsApi.create({
        name: formData.title || "Untitled Campaign",
        template_id: "", // template selected via UI preset; empty = custom
        languages: [formData.primaryLanguage.toLowerCase(), formData.secondaryLanguage.toLowerCase()],
        event_details: {
          event_name: formData.title,
          date: formData.date,
          venue: formData.venue,
        },
      } as any);

      // 2. Upload contacts CSV if provided
      if (recipientFile) {
        setSubmitStatus("Uploading contacts…");
        await campaignsApi.importContacts(campaign.id, recipientFile);
      }

      // 3. Trigger prepare (translation + TTS)
      setSubmitStatus("Preparing campaign…");
      await campaignsApi.prepare(campaign.id);

      // 4. Poll for readiness (max 60 s, every 3 s)
      setSubmitStatus("Waiting for campaign to become ready…");
      let ready = false;
      for (let i = 0; i < 20; i++) {
        await new Promise((r) => setTimeout(r, 3000));
        const detail = await campaignsApi.get(campaign.id);
        const r = (detail as any).readiness;
        if (detail.status === "ready" || r?.can_launch === true) {
          ready = true;
          break;
        }
      }

      if (!ready) {
        setSubmitError(
          "Campaign preparation timed out. You can launch it manually from the campaign page."
        );
        setIsSubmitting(false);
        return;
      }

      // 5. Launch
      setSubmitStatus("Launching campaign…");
      await campaignsApi.launch(campaign.id);

      setSubmitStatus("Campaign launched! Redirecting…");
      setTimeout(() => router.push(`/campaigns/${campaign.id}`), 1200);
    } catch (e: unknown) {
      setSubmitError(`Error: ${e instanceof Error ? e.message : String(e)}`);
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

  const renderError = (field: string) => (
    validationErrors[field] ? (
      <p className="text-[11px] text-red-600 mt-1.5 font-mono bg-red-50/50 px-2 py-1 rounded border border-red-100">{validationErrors[field]}</p>
    ) : null
  );

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Stepper Header */}
      <div className="grid grid-cols-4 gap-2 border-b border-stone-200 pb-6">
        {STEPS.map((step, idx) => {
          const isDone = idx < currentStep;
          const isCurrent = idx === currentStep;
          return (
            <div
              key={step}
              onClick={() => idx < currentStep && setCurrentStep(idx)}
              className={`flex items-center gap-3 transition-transform ${idx < currentStep ? "cursor-pointer hover:scale-105" : ""}`}
            >
              <div
                className={`btn-3d w-8 h-8 rounded-full flex items-center justify-center text-xs font-mono font-bold transition-all ${
                  isCurrent
                    ? "bg-brand-red !text-white ring-4 ring-red-100 shadow-md scale-110"
                    : isDone
                    ? "bg-stone-900 !text-white shadow-xs"
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

      {/* Step Content */}
      <div className="card-3d bg-white rounded-xl border border-stone-200 p-6 sm:p-8 shadow-sm">
        {currentStep === 0 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-stone-900">Event Details</h2>
              <p className="text-xs text-stone-500 mt-1">Specify the core event parameters that will be interpolated into the speech model.</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="sm:col-span-2">
                <label className="block text-xs font-mono uppercase text-stone-600 mb-1.5">Campaign Title</label>
                <input
                  type="text"
                  placeholder="e.g., Annual Tech Summit VIP Invitation"
                  value={formData.title}
                  onChange={(e) => updateField("title", e.target.value)}
                  className={`w-full px-3.5 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-red/20 focus:border-brand-red ${validationErrors.title ? "border-red-300" : "border-stone-300"}`}
                />
                {renderError("title")}
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-stone-600 mb-1.5">Event Type</label>
                <select
                  value={formData.eventType}
                  onChange={(e) => updateField("eventType", e.target.value)}
                  className={`w-full px-3.5 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-red/20 focus:border-brand-red bg-white ${validationErrors.eventType ? "border-red-300" : "border-stone-300"}`}
                >
                  <option>Invitation</option>
                  <option>Reminder</option>
                  <option>Update</option>
                  <option>Feedback</option>
                </select>
                {renderError("eventType")}
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-stone-600 mb-1.5">Date</label>
                <input
                  type="date"
                  value={formData.date}
                  onChange={(e) => updateField("date", e.target.value)}
                  className={`w-full px-3.5 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-red/20 focus:border-brand-red ${validationErrors.date ? "border-red-300" : "border-stone-300"}`}
                />
                {renderError("date")}
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-stone-600 mb-1.5">Time</label>
                <input
                  type="time"
                  value={formData.time}
                  onChange={(e) => updateField("time", e.target.value)}
                  className={`w-full px-3.5 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-red/20 focus:border-brand-red ${validationErrors.time ? "border-red-300" : "border-stone-300"}`}
                />
                {renderError("time")}
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-stone-600 mb-1.5">RSVP Deadline</label>
                <input
                  type="date"
                  value={formData.rsvpDeadline}
                  onChange={(e) => updateField("rsvpDeadline", e.target.value)}
                  className="w-full px-3.5 py-2 text-sm border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-red/20 focus:border-brand-red"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-xs font-mono uppercase text-stone-600 mb-1.5">Venue / Location</label>
                <input
                  type="text"
                  placeholder="e.g., Grand Hyatt Ballroom, Mumbai"
                  value={formData.venue}
                  onChange={(e) => updateField("venue", e.target.value)}
                  className={`w-full px-3.5 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-red/20 focus:border-brand-red ${validationErrors.venue ? "border-red-300" : "border-stone-300"}`}
                />
                {renderError("venue")}
              </div>
            </div>
          </div>
        )}

        {currentStep === 1 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-stone-900">Recipient Audience</h2>
              <p className="text-xs text-stone-500 mt-1">Upload contacts CSV or select a saved contact audience.</p>
            </div>

            <div className={`border-2 border-dashed rounded-xl p-8 text-center bg-stone-50/50 hover:bg-stone-50 transition-colors ${validationErrors.recipientsFile ? "border-red-300 bg-red-50/10" : "border-stone-200"}`}>
              <div className="w-12 h-12 bg-red-50 text-brand-red rounded-full flex items-center justify-center mx-auto mb-3 font-mono text-lg font-bold">
                CSV
              </div>
              <p className="text-sm font-medium text-stone-800">Upload your recipient list (.csv)</p>
              <p className="text-xs text-stone-500 mt-1 max-w-sm mx-auto">
                Required columns: <code className="text-stone-700 bg-stone-100 px-1 py-0.5 rounded">phone</code>, <code className="text-stone-700 bg-stone-100 px-1 py-0.5 rounded">name</code>, <code className="text-stone-700 bg-stone-100 px-1 py-0.5 rounded">language</code>, <code className="text-stone-700 bg-stone-100 px-1 py-0.5 rounded">consent</code>, <code className="text-stone-700 bg-stone-100 px-1 py-0.5 rounded">dnd</code>
              </p>
              <label className="mt-4 inline-block px-4 py-2 bg-stone-900 text-white text-xs font-mono font-medium rounded-lg cursor-pointer hover:bg-stone-800 transition-colors">
                Choose CSV File
                <input
                  type="file"
                  accept=".csv"
                  className="hidden"
                  onChange={(e) => handleFileSelect(e.target.files?.[0] ?? null)}
                />
              </label>
              {formData.recipientsFile && (
                <div className="mt-3 inline-flex items-center gap-2 text-xs font-mono text-emerald-700 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
                  <span>Uploaded: {formData.recipientsFile}</span>
                  <span className="font-bold">({formData.recipientCount} contacts detected)</span>
                </div>
              )}
              {csvError && (
                <p className="mt-3 text-xs text-red-600 font-mono">{csvError}</p>
              )}
              {validationErrors.recipientsFile && !csvError && (
                <p className="mt-3 text-xs text-red-600 font-mono">{validationErrors.recipientsFile}</p>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-stone-200">
              <div>
                <label className="block text-xs font-mono uppercase text-stone-600 mb-1.5">Primary Language</label>
                <select
                  value={formData.primaryLanguage}
                  onChange={(e) => updateField("primaryLanguage", e.target.value)}
                  className={`w-full px-3.5 py-2 text-sm border rounded-lg bg-white ${validationErrors.primaryLanguage ? "border-red-300" : "border-stone-300"}`}
                >
                  <option>Hindi</option>
                  <option>English</option>
                  <option>Tamil</option>
                  <option>Telugu</option>
                  <option>Bengali</option>
                  <option>Marathi</option>
                  <option>Kannada</option>
                  <option>Gujarati</option>
                  <option>Malayalam</option>
                </select>
                {renderError("primaryLanguage")}
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-stone-600 mb-1.5">Fallback Language</label>
                <select
                  value={formData.secondaryLanguage}
                  onChange={(e) => updateField("secondaryLanguage", e.target.value)}
                  className="w-full px-3.5 py-2 text-sm border border-stone-300 rounded-lg bg-white"
                >
                  <option>English</option>
                  <option>Hindi</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {currentStep === 2 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-stone-900">Voice Script & AI Synthesis</h2>
              <p className="text-xs text-stone-500 mt-1">Craft the spoken invitation and choose your high-fidelity neural voice profile.</p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-mono uppercase text-stone-600 mb-1.5">Voice Engine Profile</label>
                <select
                  value={formData.voice}
                  onChange={(e) => updateField("voice", e.target.value)}
                  className={`w-full px-3.5 py-2 text-sm border rounded-lg bg-white font-mono ${validationErrors.voice ? "border-red-300" : "border-stone-300"}`}
                >
                  <option>Sarvam - Hindi Natural (Female - Bulbul)</option>
                  <option>Sarvam - Hindi Formal (Male - Arjun)</option>
                  <option>ElevenLabs - Multilingual v2 (Aria)</option>
                  <option>ElevenLabs - Multilingual v2 (Roger)</option>
                  <option>OpenAI - TTS-1-HD (Nova)</option>
                </select>
                {renderError("voice")}
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-mono uppercase text-stone-600">Voice Script</label>
                  <div className="flex gap-1.5">
                    {["{name}", "{event_name}", "{date}", "{venue}"].map((tag) => (
                      <button
                        key={tag}
                        type="button"
                        onClick={() => updateField("scriptText", formData.scriptText + " " + tag)}
                        className="text-[11px] font-mono px-2 py-0.5 bg-stone-100 hover:bg-stone-200 text-stone-700 rounded border border-stone-200"
                      >
                        +{tag}
                      </button>
                    ))}
                  </div>
                </div>
                <textarea
                  rows={5}
                  value={formData.scriptText}
                  onChange={(e) => updateField("scriptText", e.target.value)}
                  className={`w-full px-3.5 py-2.5 text-sm font-sans border rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-red/20 focus:border-brand-red ${validationErrors.scriptText ? "border-red-300" : "border-stone-300"}`}
                />
                {renderError("scriptText")}
              </div>

              <div className="flex items-center justify-between p-3.5 bg-stone-50 rounded-lg border border-stone-200">
                <div className="text-xs text-stone-600">
                  <span className="font-semibold text-stone-800">Estimated Call Duration:</span> ~45 seconds per recipient
                </div>
                <button
                  type="button"
                  onClick={() => alert("Playing synthetic preview audio snippet...")}
                  className="px-3 py-1.5 bg-white border border-stone-300 hover:bg-stone-50 text-stone-800 text-xs font-mono font-medium rounded-md shadow-sm transition-colors"
                >
                  Play Preview
                </button>
              </div>
            </div>
          </div>
        )}

        {currentStep === 3 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-stone-900">Launch & Telephony Dispatch</h2>
              <p className="text-xs text-stone-500 mt-1">Review concurrency limits and dispatch your campaign via Exotel.</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-mono uppercase text-stone-600 mb-1.5">Concurrent Calling Channels</label>
                <select
                  value={formData.concurrency}
                  onChange={(e) => updateField("concurrency", e.target.value)}
                  className={`w-full px-3.5 py-2 text-sm border rounded-lg bg-white font-mono ${validationErrors.concurrency ? "border-red-300" : "border-stone-300"}`}
                >
                  <option value="1">1 channel (Testing / Slow)</option>
                  <option value="5">5 channels (Standard)</option>
                  <option value="10">10 channels (High Throughput)</option>
                  <option value="25">25 channels (Enterprise Bulk)</option>
                </select>
                {renderError("concurrency")}
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-stone-600 mb-1.5">Max Retries on Unanswered</label>
                <select
                  value={formData.maxRetries}
                  onChange={(e) => updateField("maxRetries", e.target.value)}
                  className={`w-full px-3.5 py-2 text-sm border rounded-lg bg-white font-mono ${validationErrors.maxRetries ? "border-red-300" : "border-stone-300"}`}
                >
                  <option value="0">No retry</option>
                  <option value="1">1 retry (after 15 mins)</option>
                  <option value="2">2 retries (after 15m, 1h)</option>
                  <option value="3">3 retries (adaptive)</option>
                </select>
                {renderError("maxRetries")}
              </div>
            </div>

            {/* Campaign Summary Box */}
            <div className="p-4 rounded-xl bg-stone-900 text-white space-y-3 font-mono text-xs">
              <div className="text-[11px] uppercase tracking-wider text-stone-400 font-bold border-b border-stone-800 pb-2">
                Dispatch Summary
              </div>
              <div className="grid grid-cols-2 gap-y-2 text-stone-300">
                <div>Campaign: <span className="text-white font-bold">{formData.title || "Untitled Event Campaign"}</span></div>
                <div>Audience: <span className="text-white font-bold">{formData.recipientCount || 1} recipients</span></div>
                <div>Primary Language: <span className="text-white font-bold">{formData.primaryLanguage}</span></div>
                <div>Voice Engine: <span className="text-white font-bold">{formData.voice.split("-")[0]}</span></div>
                <div>Telephony Trunk: <span className="text-emerald-400 font-bold">Exotel PRI Line Active</span></div>
                <div>Safety Rule: <span className="text-emerald-400 font-bold">TRAI 9AM-9PM Guard ON</span></div>
              </div>
            </div>

            {/* Submit status / error */}
            {submitStatus && (
              <p className="text-xs font-mono text-stone-700 bg-stone-50 border border-stone-200 px-3 py-2 rounded-lg">
                {submitStatus}
              </p>
            )}
            {submitError && (
              <p className="text-xs font-mono text-red-700 bg-red-50 border border-red-200 px-3 py-2 rounded-lg">
                {submitError}
              </p>
            )}
          </div>
        )}

        {/* Wizard Footer Controls */}
        <div className="flex items-center justify-between pt-6 border-t border-stone-200 mt-8">
          <button
            type="button"
            onClick={handleBack}
            disabled={currentStep === 0 || isSubmitting}
            className={`btn-3d px-6 py-2.5 text-sm font-mono font-medium rounded-lg transition-all ${
              currentStep === 0
                ? "text-stone-400 border border-stone-200 bg-stone-50 cursor-not-allowed opacity-50"
                : "text-stone-700 border border-stone-300 hover:bg-stone-100 hover:text-stone-900 shadow-sm"
            }`}
          >
            ← Back
          </button>

          <button
            type="button"
            onClick={handleNext}
            disabled={isSubmitting}
            className={`btn-3d px-8 py-2.5 text-sm font-mono font-bold uppercase tracking-wider rounded-lg shadow-md transition-all flex items-center justify-center gap-2 min-w-[200px] ${
              isSubmitting
                ? "bg-brand-red/80 text-white/90 cursor-wait opacity-80"
                : "bg-brand-red hover:bg-brand-red-hover text-white hover:shadow-lg"
            }`}
          >
            {isSubmitting ? (
              <span>{submitStatus || "Processing..."}</span>
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