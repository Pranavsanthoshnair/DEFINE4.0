"use client";

import { useState, useRef } from "react";

type Contact = { name: string; phone: string; language: string; status: "valid" | "invalid"; reason?: string };

const SAMPLE_CONTACTS: Contact[] = [
  { name: "Aarav Sharma", phone: "+91 98765 43210", language: "Hindi", status: "valid" },
  { name: "Priya Patel", phone: "+91 91234 56789", language: "Gujarati", status: "valid" },
  { name: "Suresh Kumar", phone: "+91 94440 12345", language: "Tamil", status: "valid" },
  { name: "Ananya Roy", phone: "+91 98300 98765", language: "Bengali", status: "valid" },
  { name: "Rahul Verma", phone: "+91 98111 22334", language: "Hindi", status: "valid" },
  { name: "Deepak Joshi", phone: "98765", language: "Marathi", status: "invalid", reason: "Invalid phone length" },
];

export default function ContactsPanel() {
  const [contacts, setContacts] = useState<Contact[]>(SAMPLE_CONTACTS);
  const [rawText, setRawText] = useState("");
  const [activeTab, setActiveTab] = useState<"table" | "paste">("table");
  const [isProcessing, setIsProcessing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleValidatePaste = () => {
    if (!rawText.trim()) return;
    setIsProcessing(true);
    setTimeout(() => {
      const lines = rawText.split("\n").filter((l) => l.trim().length > 0);
      const parsed: Contact[] = lines.map((line) => {
        const parts = line.split(",").map((p) => p.trim());
        const name = parts[0] || "Unknown";
        const phone = parts[1] || "";
        const language = parts[2] || "Hindi";
        const isValidPhone = phone.replace(/[^0-9]/g, "").length >= 10;
        return {
          name,
          phone,
          language,
          status: isValidPhone ? "valid" : "invalid",
          reason: isValidPhone ? undefined : "Malformed phone number",
        };
      });
      setContacts((prev) => [...parsed, ...prev]);
      setRawText("");
      setActiveTab("table");
      setIsProcessing(false);
    }, 400);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      if (text) {
        const lines = text.split("\n").filter((l) => l.trim().length > 0);
        const startIdx = lines[0].toLowerCase().includes("phone") ? 1 : 0;
        const parsed: Contact[] = lines.slice(startIdx).map((line) => {
          const parts = line.split(",").map((p) => p.trim());
          const name = parts[0] || "Unknown";
          const phone = parts[1] || "";
          const language = parts[2] || "Hindi";
          const isValidPhone = phone.replace(/[^0-9]/g, "").length >= 10;
          return {
            name,
            phone,
            language,
            status: isValidPhone ? "valid" : "invalid",
            reason: isValidPhone ? undefined : "Malformed phone number",
          };
        });
        setContacts((prev) => [...parsed, ...prev]);
      }
    };
    reader.readAsText(file);
  };

  const validCount = contacts.filter((c) => c.status === "valid").length;
  const invalidCount = contacts.filter((c) => c.status === "invalid").length;

  return (
    <div className="space-y-6">
      {/* Stats and Action Bar with 3D Depth */}
      <div className="card-3d flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-4 rounded-xl border border-stone-200 shadow-sm">
        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-stone-900"></span>
            <span>Total: <strong>{contacts.length}</strong></span>
          </div>
          <div className="flex items-center gap-1.5 text-emerald-700">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
            <span>Valid: <strong>{validCount}</strong></span>
          </div>
          {invalidCount > 0 && (
            <div className="flex items-center gap-1.5 text-brand-red">
              <span className="w-2.5 h-2.5 rounded-full bg-brand-red animate-pulse"></span>
              <span>Errors: <strong>{invalidCount}</strong></span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".csv"
            className="hidden"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="btn-3d px-3.5 py-1.5 bg-stone-100 hover:bg-stone-200 text-stone-800 text-xs font-mono font-medium rounded-lg transition-all flex items-center gap-1.5 border border-stone-200 shadow-xs"
          >
            <span>↑</span> Upload CSV
          </button>
          <button
            type="button"
            onClick={() => setActiveTab(activeTab === "paste" ? "table" : "paste")}
            className={`btn-3d px-3.5 py-1.5 text-xs font-mono font-medium rounded-lg transition-all ${
              activeTab === "paste" ? "bg-stone-900 !text-white font-bold shadow-md transform -translate-y-0.5" : "bg-stone-100 hover:bg-stone-200 text-stone-700 border border-stone-200"
            }`}
          >
            {activeTab === "paste" ? "View Table" : "Paste Raw"}
          </button>
          {contacts.length > 0 && (
            <button
              type="button"
              onClick={() => setContacts([])}
              className="btn-3d px-3 py-1.5 text-brand-red hover:bg-red-50 text-xs font-mono font-medium rounded-lg transition-colors border border-red-200"
            >
              Clear All
            </button>
          )}
        </div>
      </div>

      {/* Paste Panel */}
      {activeTab === "paste" && (
        <div className="bg-white rounded-xl border border-stone-200 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-stone-900">Paste Raw CSV / Line-Separated Contacts</h3>
              <p className="text-xs text-stone-500 mt-0.5">Format: <code>Name, Phone (+91...), Language</code></p>
            </div>
            <button
              type="button"
              onClick={() => setActiveTab("table")}
              className="text-stone-400 hover:text-stone-700 text-sm"
            >
              x
            </button>
          </div>

          <textarea
            rows={6}
            placeholder="Rohit Sharma, +919876543210, Marathi\nKavita Singh, +919988776655, Hindi"
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            className="w-full p-3 font-mono text-xs border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-red/20 focus:border-brand-red"
          />

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setActiveTab("table")}
              className="px-3 py-1.5 text-xs font-mono border border-stone-200 rounded-lg text-stone-600 hover:bg-stone-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleValidatePaste}
              disabled={isProcessing || !rawText.trim()}
              className="px-4 py-1.5 text-xs font-mono font-bold uppercase bg-brand-red hover:bg-brand-red-hover !text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {isProcessing ? "Validating..." : "Validate & Add"}
            </button>
          </div>
        </div>
      )}

      {/* Contacts Table */}
      <div className="bg-white rounded-xl border border-stone-200 overflow-hidden shadow-sm">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-stone-50 border-b border-stone-200 text-[11px] font-mono text-stone-500 uppercase tracking-wider">
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4">Contact Name</th>
              <th className="py-3 px-4">Phone Number</th>
              <th className="py-3 px-4">Language</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100 text-xs font-sans">
            {contacts.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-12 text-center text-stone-400 font-mono">
                  No contacts found. Upload a CSV or click &quot;Paste Raw&quot; to add contacts.
                </td>
              </tr>
            ) : (
              contacts.map((c, i) => (
                <tr key={i} className="hover:bg-stone-50/60 transition-colors">
                  <td className="py-3 px-4 font-mono">
                    {c.status === "valid" ? (
                      <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded text-[10px] font-semibold border border-emerald-200">
                        VALID
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-brand-red bg-red-50 px-2 py-0.5 rounded text-[10px] font-semibold border border-red-200" title={c.reason}>
                        ERROR
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4 font-medium text-stone-900">{c.name}</td>
                  <td className="py-3 px-4 font-mono text-stone-600">{c.phone}</td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-0.5 bg-stone-100 text-stone-700 rounded text-xs font-mono">
                      {c.language}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      type="button"
                      onClick={() => setContacts((prev) => prev.filter((_, idx) => idx !== i))}
                      className="text-stone-400 hover:text-brand-red text-xs font-mono transition-colors"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
