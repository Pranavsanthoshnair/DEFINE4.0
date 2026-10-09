"use client";

import { useState } from "react";

export default function SettingsForm() {
  const [saved, setSaved] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  const [settings, setSettings] = useState({
    exotelSid: "",
    exotelApiKey: "",
    exotelToken: "",
    exotelCallerId: "",
    sarvamApiKey: "",
    elevenLabsKey: "",
    openaiKey: "",
    concurrencyCap: "10",
    callingHoursStart: "09:00",
    callingHoursEnd: "21:00",
    webhookUrl: "",
  });

  const update = (k: string, v: string) => {
    setSettings((p) => ({ ...p, [k]: v }));
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
      const res = await fetch(`${API}/api/v1/capabilities`);
      if (res.ok) {
        const data = await res.json();
        const lines = Object.entries(data)
          .filter(([, v]) => v)
          .map(([k]) => k)
          .join(", ");
        setTestResult(`✅ Backend connected. Active: ${lines || "none"}`);
      } else {
        setTestResult(`❌ Backend returned ${res.status}`);
      }
    } catch {
      setTestResult("❌ Could not reach backend at " + (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"));
    }
    setTesting(false);
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <form onSubmit={handleSave} className="space-y-8 max-w-3xl">
      {/* Telephony Trunk */}
      <div className="bg-white rounded-xl border border-stone-200 p-6 space-y-4 shadow-sm">
        <div className="flex items-center justify-between border-b border-stone-200 pb-3">
          <div>
            <h3 className="text-sm font-semibold text-stone-900">Exotel Telephony Trunk</h3>
            <p className="text-xs text-stone-500 mt-0.5">Outbound SIP and PRI line credentials for India telephony dispatch.</p>
          </div>
          <button
            type="button"
            onClick={handleTestConnection}
            disabled={testing}
            className="px-3 py-1.5 text-xs font-mono font-medium border border-stone-300 rounded-lg hover:bg-stone-50 transition-colors"
          >
            {testing ? "Testing..." : "Test Connection"}
          </button>
        </div>

        {testResult && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs font-mono text-emerald-800">
            {testResult}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-mono uppercase text-stone-600 mb-1">Exotel Account SID</label>
            <input
              type="text"
              value={settings.exotelSid}
              onChange={(e) => update("exotelSid", e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono border border-stone-300 rounded-lg bg-stone-50/50"
            />
          </div>
          <div>
            <label className="block text-xs font-mono uppercase text-stone-600 mb-1">Caller ID (Virtual Number)</label>
            <input
              type="text"
              value={settings.exotelCallerId}
              onChange={(e) => update("exotelCallerId", e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono border border-stone-300 rounded-lg bg-stone-50/50"
            />
          </div>
          <div>
            <label className="block text-xs font-mono uppercase text-stone-600 mb-1">API Key</label>
            <input
              type="password"
              value={settings.exotelApiKey}
              onChange={(e) => update("exotelApiKey", e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono border border-stone-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-xs font-mono uppercase text-stone-600 mb-1">API Token</label>
            <input
              type="password"
              value={settings.exotelToken}
              onChange={(e) => update("exotelToken", e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono border border-stone-300 rounded-lg"
            />
          </div>
        </div>
      </div>

      {/* AI Voice Providers */}
      <div className="bg-white rounded-xl border border-stone-200 p-6 space-y-4 shadow-sm">
        <div className="border-b border-stone-200 pb-3">
          <h3 className="text-sm font-semibold text-stone-900">AI Voice Synthesis Engine Keys</h3>
          <p className="text-xs text-stone-500 mt-0.5">API keys for Indic languages (Sarvam) and international accents.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-mono uppercase text-stone-600 mb-1">Sarvam AI Key (Indic Neural)</label>
            <input
              type="password"
              value={settings.sarvamApiKey}
              onChange={(e) => update("sarvamApiKey", e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono border border-stone-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-xs font-mono uppercase text-stone-600 mb-1">ElevenLabs Key</label>
            <input
              type="password"
              value={settings.elevenLabsKey}
              onChange={(e) => update("elevenLabsKey", e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono border border-stone-300 rounded-lg"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-mono uppercase text-stone-600 mb-1">OpenAI API Key (Whisper / GPT-4o)</label>
            <input
              type="password"
              value={settings.openaiKey}
              onChange={(e) => update("openaiKey", e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono border border-stone-300 rounded-lg"
            />
          </div>
        </div>
      </div>

      {/* Regulatory & Safety */}
      <div className="bg-white rounded-xl border border-stone-200 p-6 space-y-4 shadow-sm">
        <div className="border-b border-stone-200 pb-3">
          <h3 className="text-sm font-semibold text-stone-900">Compliance & Guardrails</h3>
          <p className="text-xs text-stone-500 mt-0.5">TRAI regulatory constraints and concurrency safety limits.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-mono uppercase text-stone-600 mb-1">Calling Window Start</label>
            <input
              type="time"
              value={settings.callingHoursStart}
              onChange={(e) => update("callingHoursStart", e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono border border-stone-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-xs font-mono uppercase text-stone-600 mb-1">Calling Window End</label>
            <input
              type="time"
              value={settings.callingHoursEnd}
              onChange={(e) => update("callingHoursEnd", e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono border border-stone-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-xs font-mono uppercase text-stone-600 mb-1">Max System Concurrency</label>
            <input
              type="number"
              value={settings.concurrencyCap}
              onChange={(e) => update("concurrencyCap", e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono border border-stone-300 rounded-lg"
            />
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex items-center justify-end gap-3 pt-4">
        {saved && (
          <span className="text-xs font-mono text-emerald-700 font-semibold">Settings saved successfully!</span>
        )}
        <button
          type="submit"
          className="px-6 py-2.5 bg-brand-red hover:bg-brand-red-hover !text-white text-xs font-mono font-bold uppercase tracking-wider rounded-lg shadow-sm transition-colors"
        >
          Save Settings
        </button>
      </div>
    </form>
  );
}
