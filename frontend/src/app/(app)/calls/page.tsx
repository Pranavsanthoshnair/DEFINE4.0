"use client";

import Image from "next/image";
import PageHeader from "@/components/ui/PageHeader";
import { useDemo } from "@/context/DemoModeContext";
import { DEMO_CALLS } from "@/lib/demo-data";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const INTENT_COLOR: Record<string, string> = {
  confirm:    "#16a34a",
  declined:   "#dc2626",
  call_later: "#d97706",
  no_answer:  "#94a3b8",
  unclear:    "#64748b",
};

type CallRecord = {
  id: string;
  contact?: string;
  intent?: string;
  confidence?: number;
  method?: string;
  lang?: string;
  transcript?: string;
  created_at?: string;
  duration_s?: number;
  campaign_name?: string;
};

export default function CallsPage() {
  const { isDemo } = useDemo();
  const [calls, setCalls]   = useState<CallRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isDemo) { setCalls(DEMO_CALLS); setLoading(false); return; }
    setLoading(true);
    fetch(`${API}/api/v1/calls/?limit=50`, { signal: AbortSignal.timeout(8000) })
      .then(r => r.ok ? r.json() : [])
      .then(d => setCalls(Array.isArray(d) ? d : (d.items ?? [])))
      .catch(() => setCalls([]))
      .finally(() => setLoading(false));
  }, [isDemo]);

  return (
    <div className="page-in w-full">
      <PageHeader
        eyebrow="call history"
        title="Call History"
        subtitle={isDemo ? "Demo calls — press Space×5 to switch to live mode." : "Every call attempt, with its outcome and AI intent."}
        tagline="Every ring, remembered."
        bubble={isDemo ? "Demo 🎭" : "Live 🔴"}
        mascot="boy"
      />

      <div className="glass" style={{ padding: "18px 20px", overflowX: "auto" }}>
        <table className="vtable" style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid rgba(23,38,58,.08)" }}>
              {["Contact", "Intent", "Confidence", "Method", "Language", "Transcript"].map(h => (
                <th key={h} style={{ padding: "10px 14px", fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 11, color: "#8A9BB0", letterSpacing: ".08em", textTransform: "uppercase", textAlign: "left" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} style={{ textAlign: "center", padding: "32px", color: "#8A9BB0", fontFamily: "Manrope, sans-serif" }}>Loading…</td></tr>
            ) : calls.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", paddingTop: 40, paddingBottom: 40 }}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
                    <Image src="/veylo-boy.png" alt="" width={80} height={80} style={{ objectFit: "contain", height: "auto", width: "auto" }} />
                    <p style={{ margin: 0, fontFamily: "Manrope, sans-serif", fontWeight: 600, fontSize: 14, color: "#4A5B6E" }}>
                      No calls yet — launch a campaign to see history here.
                    </p>
                  </div>
                </td>
              </tr>
            ) : calls.map(c => (
              <tr key={c.id} style={{ borderBottom: "1px solid rgba(23,38,58,.05)" }}>
                <td style={{ padding: "11px 14px", fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 13, color: "#17263A" }}>{c.contact ?? "—"}</td>
                <td style={{ padding: "11px 14px" }}>
                  <span style={{ background: `${INTENT_COLOR[c.intent ?? "unclear"]}15`, color: INTENT_COLOR[c.intent ?? "unclear"], fontWeight: 700, fontSize: 10, padding: "3px 8px", borderRadius: 6, letterSpacing: ".06em", textTransform: "uppercase" }}>
                    {c.intent ?? "—"}
                  </span>
                </td>
                <td style={{ padding: "11px 14px", fontFamily: "Manrope, monospace", fontSize: 12, color: "#5A6E84" }}>
                  {c.confidence != null ? `${(c.confidence * 100).toFixed(0)}%` : "—"}
                </td>
                <td style={{ padding: "11px 14px", fontFamily: "Manrope, sans-serif", fontSize: 11, color: "#8A9BB0" }}>{c.method ?? "—"}</td>
                <td style={{ padding: "11px 14px", fontFamily: "Manrope, sans-serif", fontSize: 12, color: "#5A6E84" }}>{c.lang ?? "—"}</td>
                <td style={{ padding: "11px 14px", fontFamily: "Manrope, sans-serif", fontSize: 12, color: "#5A6E84", fontStyle: "italic", maxWidth: 200 }}>
                  {c.transcript ? `"${c.transcript}"` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="pgf"><span>VEYLO / CALL HISTORY</span><i>✳</i></div>
    </div>
  );
}
