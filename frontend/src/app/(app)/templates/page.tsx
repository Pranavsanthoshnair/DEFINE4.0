"use client";

import PageHeader from "@/components/ui/PageHeader";
import { useDemo } from "@/context/DemoModeContext";
import { DEMO_TEMPLATES } from "@/lib/demo-data";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Template = {
  id: string;
  name: string;
  language?: string;
  segments?: string[];
  status?: string;
  used_in?: number;
};

export default function TemplatesPage() {
  const { isDemo } = useDemo();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading]     = useState(true);

  useEffect(() => {
    if (isDemo) { setTemplates(DEMO_TEMPLATES); setLoading(false); return; }
    setLoading(true);
    fetch(`${API}/api/templates`, { signal: AbortSignal.timeout(8000) })
      .then(r => r.ok ? r.json() : [])
      .then(d => setTemplates(Array.isArray(d) ? d : []))
      .catch(() => setTemplates([]))
      .finally(() => setLoading(false));
  }, [isDemo]);

  return (
    <div className="w-full">
      <PageHeader
        eyebrow="templates"
        title="Voice Templates"
        subtitle={isDemo ? "Demo templates — press Space×5 to switch to live mode." : "Dynamic AI voice scripts for your campaigns."}
        mascot="girl"
        bubble={isDemo ? "Demo 🎭" : "Live data 🔴"}
      />

      {loading ? (
        <div style={{ padding: "48px 24px", textAlign: "center", color: "#8A9BB0", fontFamily: "Manrope, sans-serif" }}>Loading templates…</div>
      ) : templates.length === 0 ? (
        <div style={{ background: "#fff", borderRadius: 16, border: "1px solid rgba(23,38,58,.08)", padding: "56px 24px", textAlign: "center" }}>
          <p style={{ fontFamily: "Manrope, sans-serif", fontSize: 15, fontWeight: 700, color: "#17263A", margin: "0 0 8px" }}>No templates yet</p>
          <p style={{ fontFamily: "Manrope, sans-serif", fontSize: 13, color: "#8A9BB0", margin: 0 }}>Templates are auto-created when you create a campaign.</p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
          {templates.map(t => (
            <div key={t.id} style={{ background: "#fff", borderRadius: 16, border: "1px solid rgba(23,38,58,.08)", padding: "20px", boxShadow: "0 1px 4px rgba(23,38,58,.05)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                <h3 style={{ margin: 0, fontFamily: "Manrope, sans-serif", fontWeight: 800, fontSize: 14, color: "#17263A", lineHeight: 1.3 }}>{t.name}</h3>
                <span style={{
                  background: t.status === "approved" ? "#dcfce7" : "#fef9c3",
                  color: t.status === "approved" ? "#16a34a" : "#854d0e",
                  fontWeight: 700, fontSize: 10, padding: "3px 8px", borderRadius: 6,
                  letterSpacing: ".06em", textTransform: "uppercase", flexShrink: 0, marginLeft: 8,
                }}>
                  {t.status ?? "draft"}
                </span>
              </div>
              <p style={{ margin: "0 0 10px", fontFamily: "Manrope, sans-serif", fontSize: 12, color: "#8A9BB0" }}>
                Languages: <strong style={{ color: "#5A6E84" }}>{t.language ?? "—"}</strong>
              </p>
              {t.segments && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 10 }}>
                  {t.segments.map(s => (
                    <span key={s} style={{ background: "rgba(23,38,58,.05)", color: "#5A6E84", fontSize: 10, fontWeight: 600, padding: "2px 7px", borderRadius: 4, fontFamily: "Manrope, sans-serif" }}>
                      {s}
                    </span>
                  ))}
                </div>
              )}
              <p style={{ margin: 0, fontFamily: "Manrope, sans-serif", fontSize: 11, color: "#A0AEC0" }}>
                Used in {t.used_in ?? 0} campaign{(t.used_in ?? 0) !== 1 ? "s" : ""}
              </p>
            </div>
          ))}
        </div>
      )}

      <div className="pgf" style={{ marginTop: 32 }}><span>VEYLO / TEMPLATES</span><i>✳</i></div>
    </div>
  );
}
