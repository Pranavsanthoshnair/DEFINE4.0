"use client";

import { useState } from "react";

const KINDS = ["invitation", "reminder", "update"] as const;
const LANGS = ["Hindi", "English", "Tamil", "Telugu", "Bengali", "Marathi", "Kannada", "Gujarati"] as const;

const TEMPLATES: Record<string, string> = {
  "invitation-Hindi": "Namaskar {name} ji, aapko {event_name} ke liye aamantrit kiya jata hai jo {date} ko {venue} par aayojit hoga. Kripya apna RSVP darj karein.",
  "invitation-English": "Hello {name}, you are cordially invited to {event_name} scheduled on {date} at {venue}. Please confirm your attendance.",
  "reminder-Hindi": "Namaskar {name} ji, yeh ek anurodh hai ki {event_name} kal {time} baje {venue} par hoga.",
  "reminder-English": "Hello {name}, this is a gentle reminder that {event_name} is happening tomorrow at {time}, {venue}.",
  "update-Hindi": "Namaskar {name} ji, {event_name} ke samay aur venue mein badlav kiya gaya hai. Naya samay: {time}.",
  "update-English": "Hello {name}, please note the updated schedule for {event_name}. Venue: {venue}.",
};

export default function TemplateEditor() {
  const [kind, setKind] = useState<typeof KINDS[number]>("invitation");
  const [lang, setLang] = useState<typeof LANGS[number]>("Hindi");
  const [scriptText, setScriptText] = useState(TEMPLATES["invitation-Hindi"]);
  const [saved, setSaved] = useState(false);

  const handleKindOrLangChange = (newKind: typeof KINDS[number], newLang: typeof LANGS[number]) => {
    setKind(newKind);
    setLang(newLang);
    const key = `${newKind}-${newLang}`;
    setScriptText(TEMPLATES[key] || `Namaskar {name}, {event_name} update for ${newLang}.`);
  };

  const insertTag = (tag: string) => {
    setScriptText((prev) => prev + " " + tag);
  };

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="space-y-6">
      {/* Template Kinds */}
      <div className="flex flex-wrap items-center gap-2 border-b border-stone-200 pb-4">
        {KINDS.map((k) => (
          <button
            key={k}
            type="button"
            onClick={() => handleKindOrLangChange(k, lang)}
            className={`px-3 py-1.5 text-xs font-mono font-bold rounded-lg uppercase tracking-wider transition-all ${
              kind === k
                ? "bg-stone-900 !text-white shadow-sm"
                : "bg-stone-100 text-stone-700 hover:bg-stone-200"
            }`}
          >
            {k}
          </button>
        ))}
      </div>

      {/* Language Selector */}
      <div className="flex flex-wrap items-center gap-1.5">
        {LANGS.map((l) => (
          <button
            key={l}
            type="button"
            onClick={() => handleKindOrLangChange(kind, l)}
            className={`px-2.5 py-1 text-xs font-mono rounded-md transition-all ${
              lang === l
                ? "bg-brand-red !text-white font-bold shadow-sm"
                : "bg-stone-50 border border-stone-200 text-stone-700 hover:bg-stone-100 font-medium"
            }`}
          >
            {l}
          </button>
        ))}
      </div>

      {/* Editor Box */}
      <div className="bg-white rounded-xl border border-stone-200 p-6 space-y-4 shadow-sm">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-stone-900">
            Voice Script Template - <span className="text-brand-red capitalize">{kind}</span> ({lang})
          </h3>
          <div className="flex gap-1">
            {["{name}", "{event_name}", "{date}", "{time}", "{venue}", "{rsvp_link}"].map((tag) => (
              <button
                key={tag}
                type="button"
                onClick={() => insertTag(tag)}
                className="text-[11px] font-mono px-2 py-0.5 bg-stone-100 hover:bg-stone-200 text-stone-700 rounded border border-stone-200"
              >
                +{tag}
              </button>
            ))}
          </div>
        </div>

        <textarea
          rows={6}
          value={scriptText}
          onChange={(e) => setScriptText(e.target.value)}
          className="w-full p-3 font-mono text-sm border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-red/20 focus:border-brand-red"
        />

        <div className="flex items-center justify-between pt-2">
          <div className="text-xs text-stone-500 font-mono">
            Variables detected: {["{name}", "{event_name}", "{date}", "{time}", "{venue}", "{rsvp_link}"].filter((t) => scriptText.includes(t)).join(", ") || "None"}
          </div>

          <div className="flex items-center gap-3">
            {saved && (
              <span className="text-xs font-mono text-emerald-700 font-medium">Template Saved!</span>
            )}
            <button
              type="button"
              onClick={handleSave}
              className="px-4 py-2 bg-stone-900 hover:bg-stone-800 text-white text-xs font-mono font-semibold uppercase tracking-wider rounded-lg transition-colors shadow-sm"
            >
              Save Template
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
