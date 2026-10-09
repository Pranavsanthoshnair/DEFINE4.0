"use client";

import PageHeader from "@/components/ui/PageHeader";
import { useDemo } from "@/context/DemoModeContext";
import { DEMO_CONTACTS } from "@/lib/demo-data";
import { useEffect, useState } from "react";
import AddContactsDrawer from "@/components/campaigns/AddContactsDrawer";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const STATUS_COLORS: Record<string, { bg: string; color: string }> = {
  confirmed:  { bg: "#dcfce7", color: "#16a34a" },
  declined:   { bg: "#fee2e2", color: "#dc2626" },
  call_later: { bg: "#fef9c3", color: "#854d0e" },
  no_answer:  { bg: "#f1f5f9", color: "#475569" },
  pending:    { bg: "#f8fafc", color: "#94a3b8" },
};

type Contact = {
  id: string;
  name?: string;
  phone?: string;
  phone_last4?: string;
  language?: string;
  segment?: string;
  status?: string;
  campaign?: string;
};

export default function ContactsPage() {
  const { isDemo } = useDemo();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [search, setSearch]     = useState("");
  const [showAddDrawer, setShowAddDrawer] = useState(false);

  const load = () => {
    if (isDemo) { setContacts(DEMO_CONTACTS); setLoading(false); return; }
    setLoading(true);
    setError(null);
    fetch(`${API}/api/v1/contacts/`, { signal: AbortSignal.timeout(8000) })
      .then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
      .then(d => setContacts(Array.isArray(d) ? d : (d.items ?? [])))
      .catch(e => { if (e?.name !== "AbortError") setError(String(e)); })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [isDemo]);

  const filtered = contacts.filter(c =>
    !search ||
    c.name?.toLowerCase().includes(search.toLowerCase()) ||
    c.language?.toLowerCase().includes(search.toLowerCase()) ||
    c.status?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto" }}>
      <PageHeader
        eyebrow="contacts"
        title="Audience & Contacts"
        subtitle={isDemo ? "Demo contacts — press Space×5 to switch to live mode." : "All contacts across your campaigns."}
        mascot="girl"
        bubble={isDemo ? "Demo 🎭" : "Real data 🔴"}
        action={
          <button
            onClick={() => setShowAddDrawer(true)}
            style={{ background: "#EA1D2C", color: "#fff", border: "none", borderRadius: 8, padding: "9px 18px", fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 13, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 8 }}
          >
            + Add Contacts
          </button>
        }
      />

      {/* Search */}
      <div style={{ marginBottom: 16 }}>
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search by name, language, status…"
          style={{ width: "100%", maxWidth: 380, border: "1.5px solid rgba(23,38,58,.12)", borderRadius: 8, padding: "9px 14px", fontFamily: "Manrope, sans-serif", fontSize: 13, boxSizing: "border-box" }}
        />
      </div>

      <div style={{ background: "#fff", borderRadius: 16, border: "1px solid rgba(23,38,58,.08)", overflow: "hidden", boxShadow: "0 1px 4px rgba(23,38,58,.06)" }}>
        {loading ? (
          <div style={{ padding: "48px 24px", textAlign: "center", color: "#8A9BB0", fontFamily: "Manrope, sans-serif" }}>Loading contacts…</div>
        ) : error ? (
          <div style={{ padding: "48px 24px", textAlign: "center", color: "#EA1D2C", fontFamily: "Manrope, sans-serif", fontSize: 13 }}>
            {error} — import contacts via a campaign CSV
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: "56px 24px", textAlign: "center", fontFamily: "Manrope, sans-serif" }}>
            <p style={{ fontSize: 15, fontWeight: 700, color: "#17263A", margin: "0 0 8px" }}>{search ? "No matches" : "No contacts yet"}</p>
            <p style={{ fontSize: 13, color: "#8A9BB0", margin: 0 }}>
              {search ? "Try a different search." : <><button onClick={() => setShowAddDrawer(true)} style={{ background: "none", border: "none", color: "#EA1D2C", fontWeight: 600, cursor: "pointer", fontSize: 13, padding: 0 }}>Add your first contact</button> to get started.</>}
            </p>
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#F8F9FA", borderBottom: "1px solid rgba(23,38,58,.08)" }}>
                {["Name", "Language", "Segment", "Status", "Campaign"].map(h => (
                  <th key={h} style={{ padding: "12px 16px", fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 11, color: "#8A9BB0", letterSpacing: ".08em", textTransform: "uppercase", textAlign: "left" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(c => {
                const s = STATUS_COLORS[c.status ?? "pending"] ?? { bg: "#f8fafc", color: "#94a3b8" };
                return (
                  <tr key={c.id} style={{ borderBottom: "1px solid rgba(23,38,58,.05)" }}>
                    <td style={{ padding: "12px 16px", fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 13, color: "#17263A" }}>
                      {c.name ?? "—"}
                      {(c.phone ?? c.phone_last4) && <div style={{ fontWeight: 400, fontSize: 11, color: "#8A9BB0" }}>{c.phone ?? `••••${c.phone_last4}`}</div>}
                    </td>
                    <td style={{ padding: "12px 16px", fontFamily: "Manrope, sans-serif", fontSize: 12, color: "#5A6E84" }}>{c.language ?? "—"}</td>
                    <td style={{ padding: "12px 16px", fontFamily: "Manrope, sans-serif", fontSize: 12, color: "#5A6E84" }}>{c.segment ?? "—"}</td>
                    <td style={{ padding: "12px 16px" }}>
                      <span style={{ background: s.bg, color: s.color, fontWeight: 700, fontSize: 10, padding: "3px 8px", borderRadius: 6, letterSpacing: ".06em", textTransform: "uppercase" }}>
                        {c.status ?? "pending"}
                      </span>
                    </td>
                    <td style={{ padding: "12px 16px", fontFamily: "Manrope, sans-serif", fontSize: 12, color: "#8A9BB0" }}>{c.campaign ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <div style={{ marginTop: 12, fontFamily: "Manrope, sans-serif", fontSize: 12, color: "#8A9BB0" }}>
        {filtered.length} contact{filtered.length !== 1 ? "s" : ""}{search ? " matching" : ""} · {isDemo ? "Demo data" : "Live from Supabase"}
      </div>

      {/* Add contacts drawer — standalone mode with campaign picker */}
      {showAddDrawer && (
        <AddContactsDrawer
          campaignId={null}
          onClose={() => setShowAddDrawer(false)}
          onSuccess={() => { setShowAddDrawer(false); load(); }}
        />
      )}
    </div>
  );
}
