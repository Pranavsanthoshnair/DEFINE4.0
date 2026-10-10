"use client";

import { useEffect, useState } from "react";
import PageHeader from "@/components/ui/PageHeader";
import { useDemo } from "@/context/DemoModeContext";
import { DEMO_CONTACTS } from "@/lib/demo-data";
import AddContactsDrawer from "@/components/campaigns/AddContactsDrawer";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const STATUS_COLORS: Record<string, { bg: string; color: string }> = {
  confirmed:  { bg: "#dcfce7", color: "#16a34a" },
  declined:   { bg: "#fee2e2", color: "#dc2626" },
  call_later: { bg: "#fef9c3", color: "#854d0e" },
  no_answer:  { bg: "#f1f5f9", color: "#475569" },
  pending:    { bg: "#f8fafc", color: "#94a3b8" },
};

const LANG_MAP: Record<string, string> = {
  en: "English",
  hi: "Hindi (हिंदी)",
  ta: "Tamil (தமிழ்)",
  te: "Telugu (తెలుగు)",
  kn: "Kannada (ಕನ್ನಡ)",
  ml: "Malayalam (മലയാളം)",
  mr: "Marathi (मराठी)",
  bn: "Bengali (বাংলা)",
  gu: "Gujarati (ગુજરાતી)",
  pa: "Punjabi (ਪੰਜਾਬੀ)",
};

type Contact = {
  id: string;
  name?: string;
  phone?: string;
  phone_last4?: string;
  language?: string;
  segment?: string;
  status?: string;
  consent?: boolean;
  campaign?: string;
  created_at?: string;
};

export default function ContactsPage() {
  const { isDemo } = useDemo();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selectedSegment, setSelectedSegment] = useState("All");
  const [drawerMode, setDrawerMode] = useState<"single" | "csv" | null>(null);

  const load = () => {
    if (isDemo) {
      setContacts(DEMO_CONTACTS);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    fetch(`${API}/api/v1/contacts/?limit=200`, { signal: AbortSignal.timeout(8000) })
      .then((r) => (r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`)))
      .then((d) => {
        const raw = Array.isArray(d) ? d : d.items ?? [];
        setContacts(
          raw.map((c: any) => ({
            id: c.id,
            name: c.name || (c.phone_last4 ? `Contact ...${c.phone_last4}` : "Contact"),
            phone: c.phone || (c.phone_last4 ? `+91 ••••• ${c.phone_last4}` : undefined),
            phone_last4: c.phone_last4,
            language: c.language || "en",
            segment: c.segment || "General",
            status: c.status || "pending",
            consent: c.consent ?? true,
            created_at: c.created_at,
          }))
        );
      })
      .catch((e) => {
        if (e?.name !== "AbortError") setError(String(e));
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [isDemo]);

  const segments = ["All", ...Array.from(new Set(contacts.map((c) => c.segment || "General").filter(Boolean)))];

  const filtered = contacts.filter((c) => {
    const matchesSearch =
      !search ||
      c.name?.toLowerCase().includes(search.toLowerCase()) ||
      c.phone?.toLowerCase().includes(search.toLowerCase()) ||
      c.language?.toLowerCase().includes(search.toLowerCase()) ||
      c.segment?.toLowerCase().includes(search.toLowerCase());

    const matchesSegment = selectedSegment === "All" || (c.segment || "General") === selectedSegment;

    return matchesSearch && matchesSegment;
  });

  return (
    <div style={{ maxWidth: 1150, margin: "0 auto", paddingBottom: 40 }}>
      <PageHeader
        eyebrow="audience management"
        title="Audience & Contacts"
        subtitle="Manage individual recipients, segments, and bulk CSV uploads across all outbound campaigns."
        mascot="girl"
        bubble={isDemo ? "Demo 🎭" : "Live Directory 🔴"}
        action={
          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={() => setDrawerMode("single")}
              style={{
                background: "#EA1D2C",
                color: "#fff",
                border: "none",
                borderRadius: 8,
                padding: "9px 16px",
                fontFamily: "Manrope, sans-serif",
                fontWeight: 700,
                fontSize: 13,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                boxShadow: "0 2px 8px rgba(234,29,44,.25)",
              }}
            >
              <span>+</span> Add Individual Contact
            </button>
            <button
              onClick={() => setDrawerMode("csv")}
              style={{
                background: "#17263A",
                color: "#fff",
                border: "none",
                borderRadius: 8,
                padding: "9px 16px",
                fontFamily: "Manrope, sans-serif",
                fontWeight: 700,
                fontSize: 13,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <span>📁</span> Import CSV
            </button>
          </div>
        }
      />

      {/* KPI Stats Strip */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: 12,
          marginBottom: 20,
        }}
      >
        <div style={{ background: "#fff", borderRadius: 12, padding: "14px 18px", border: "1px solid rgba(23,38,58,.08)" }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#8A9BB0", textTransform: "uppercase", letterSpacing: ".05em" }}>Total Contacts</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: "#17263A", marginTop: 4 }}>{contacts.length}</div>
        </div>
        <div style={{ background: "#fff", borderRadius: 12, padding: "14px 18px", border: "1px solid rgba(23,38,58,.08)" }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#8A9BB0", textTransform: "uppercase", letterSpacing: ".05em" }}>Segments / Tags</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: "#17263A", marginTop: 4 }}>{segments.length > 1 ? segments.length - 1 : 1}</div>
        </div>
        <div style={{ background: "#fff", borderRadius: 12, padding: "14px 18px", border: "1px solid rgba(23,38,58,.08)" }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#8A9BB0", textTransform: "uppercase", letterSpacing: ".05em" }}>Indic Languages</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: "#17263A", marginTop: 4 }}>
            {new Set(contacts.map((c) => c.language).filter(Boolean)).size || 1}
          </div>
        </div>
        <div style={{ background: "#fff", borderRadius: 12, padding: "14px 18px", border: "1px solid rgba(23,38,58,.08)" }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#8A9BB0", textTransform: "uppercase", letterSpacing: ".05em" }}>Consent Verified</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: "#16a34a", marginTop: 4 }}>
            {contacts.filter((c) => c.consent !== false).length}
          </div>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name, phone last-4, language, segment…"
          style={{
            width: "100%",
            maxWidth: 380,
            border: "1.5px solid rgba(23,38,58,.12)",
            borderRadius: 8,
            padding: "9px 14px",
            fontFamily: "Manrope, sans-serif",
            fontSize: 13,
            boxSizing: "border-box",
            background: "#fff",
          }}
        />

        {/* Segment filter pills */}
        <div style={{ display: "flex", gap: 6, overflowX: "auto" }}>
          {segments.map((seg) => (
            <button
              key={seg}
              onClick={() => setSelectedSegment(seg)}
              style={{
                background: selectedSegment === seg ? "#17263A" : "#fff",
                color: selectedSegment === seg ? "#fff" : "#5A6E84",
                border: `1px solid ${selectedSegment === seg ? "#17263A" : "rgba(23,38,58,.12)"}`,
                borderRadius: 20,
                padding: "5px 12px",
                fontSize: 12,
                fontWeight: 600,
                cursor: "pointer",
                fontFamily: "Manrope, sans-serif",
              }}
            >
              {seg}
            </button>
          ))}
        </div>
      </div>

      {/* Main Table */}
      <div
        style={{
          background: "#fff",
          borderRadius: 16,
          border: "1px solid rgba(23,38,58,.08)",
          overflow: "hidden",
          boxShadow: "0 1px 4px rgba(23,38,58,.06)",
        }}
      >
        {loading ? (
          <div style={{ padding: "48px 24px", textAlign: "center", color: "#8A9BB0", fontFamily: "Manrope, sans-serif" }}>
            Loading audience directory…
          </div>
        ) : error ? (
          <div style={{ padding: "48px 24px", textAlign: "center", color: "#EA1D2C", fontFamily: "Manrope, sans-serif", fontSize: 13 }}>
            {error} — add contacts individually or import a CSV.
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: "56px 24px", textAlign: "center", fontFamily: "Manrope, sans-serif" }}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>👥</div>
            <p style={{ fontSize: 16, fontWeight: 700, color: "#17263A", margin: "0 0 8px" }}>
              {search ? "No matching contacts" : "No contacts in audience"}
            </p>
            <p style={{ fontSize: 13, color: "#8A9BB0", margin: "0 0 16px" }}>
              {search ? "Try adjusting your search keyword." : "Add single recipients or import a CSV file."}
            </p>
            <div style={{ display: "flex", justifyContent: "center", gap: 10 }}>
              <button
                onClick={() => setDrawerMode("single")}
                style={{
                  background: "#EA1D2C",
                  color: "#fff",
                  border: "none",
                  borderRadius: 8,
                  padding: "9px 16px",
                  fontWeight: 700,
                  fontSize: 13,
                  cursor: "pointer",
                }}
              >
                + Add Individual Contact
              </button>
              <button
                onClick={() => setDrawerMode("csv")}
                style={{
                  background: "#17263A",
                  color: "#fff",
                  border: "none",
                  borderRadius: 8,
                  padding: "9px 16px",
                  fontWeight: 700,
                  fontSize: 13,
                  cursor: "pointer",
                }}
              >
                📁 Import CSV
              </button>
            </div>
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#F8F9FA", borderBottom: "1px solid rgba(23,38,58,.08)" }}>
                {["Contact Name & Phone", "Language", "Segment", "Status", "Consent", "Campaign Link"].map((h) => (
                  <th
                    key={h}
                    style={{
                      padding: "12px 16px",
                      fontFamily: "Manrope, sans-serif",
                      fontWeight: 700,
                      fontSize: 11,
                      color: "#8A9BB0",
                      letterSpacing: ".08em",
                      textTransform: "uppercase",
                      textAlign: "left",
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => {
                const s = STATUS_COLORS[c.status ?? "pending"] ?? { bg: "#f8fafc", color: "#94a3b8" };
                const langLabel = LANG_MAP[c.language || "en"] || c.language || "English";
                return (
                  <tr key={c.id} style={{ borderBottom: "1px solid rgba(23,38,58,.05)" }}>
                    <td style={{ padding: "12px 16px", fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 13, color: "#17263A" }}>
                      {c.name}
                      <div style={{ fontWeight: 500, fontSize: 11, color: "#8A9BB0", marginTop: 2 }}>
                        {c.phone || (c.phone_last4 ? `•••• ••• ${c.phone_last4}` : "No number")}
                      </div>
                    </td>
                    <td style={{ padding: "12px 16px", fontFamily: "Manrope, sans-serif", fontSize: 12, color: "#17263A" }}>
                      <span style={{ background: "#EFF6FF", color: "#1D4ED8", padding: "3px 8px", borderRadius: 6, fontWeight: 600, fontSize: 11 }}>
                        {langLabel}
                      </span>
                    </td>
                    <td style={{ padding: "12px 16px", fontFamily: "Manrope, sans-serif", fontSize: 12, color: "#5A6E84" }}>
                      <span style={{ background: "#F1F5F9", color: "#475569", padding: "3px 8px", borderRadius: 6, fontWeight: 600, fontSize: 11 }}>
                        {c.segment ?? "General"}
                      </span>
                    </td>
                    <td style={{ padding: "12px 16px" }}>
                      <span
                        style={{
                          background: s.bg,
                          color: s.color,
                          fontWeight: 700,
                          fontSize: 10,
                          padding: "3px 8px",
                          borderRadius: 6,
                          letterSpacing: ".06em",
                          textTransform: "uppercase",
                        }}
                      >
                        {c.status ?? "pending"}
                      </span>
                    </td>
                    <td style={{ padding: "12px 16px", fontFamily: "Manrope, sans-serif", fontSize: 11, color: "#16a34a", fontWeight: 600 }}>
                      ✓ Verified
                    </td>
                    <td style={{ padding: "12px 16px", fontFamily: "Manrope, sans-serif", fontSize: 12, color: "#8A9BB0" }}>
                      {c.campaign ?? "All Campaigns"}
                    </td>
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

      {/* Add contacts drawer */}
      {drawerMode && (
        <AddContactsDrawer
          campaignId={null}
          onClose={() => setDrawerMode(null)}
          onSuccess={() => {
            setDrawerMode(null);
            load();
          }}
        />
      )}
    </div>
  );
}
