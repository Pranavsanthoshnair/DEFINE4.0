"use client";

import Image from "next/image";
import PageHeader from "@/components/ui/PageHeader";
import { useDemo } from "@/context/DemoModeContext";
import { DEMO_ANALYTICS, DEMO_OVERVIEW } from "@/lib/demo-data";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function InsightsPage() {
  const { isDemo } = useDemo();
  const [analytics, setAnalytics] = useState<typeof DEMO_ANALYTICS | null>(null);
  const [overview, setOverview]   = useState<typeof DEMO_OVERVIEW | null>(null);
  const [loading, setLoading]     = useState(true);

  useEffect(() => {
    if (isDemo) {
      setAnalytics(DEMO_ANALYTICS);
      setOverview(DEMO_OVERVIEW);
      setLoading(false);
      return;
    }
    setLoading(true);
    Promise.all([
      fetch(`${API}/api/overview/`).then(r => r.ok ? r.json() : null),
      fetch(`${API}/api/v1/campaigns/?limit=1`).then(r => r.ok ? r.json() : []),
    ])
      .then(async ([summary, campaigns]) => {
        setOverview(summary);
        const list = Array.isArray(campaigns) ? campaigns : (campaigns?.items ?? campaigns?.campaigns ?? []);
        if (list[0]?.id) {
          const r = await fetch(`${API}/api/v1/analytics/${list[0].id}`);
          if (r.ok) setAnalytics(await r.json());
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [isDemo]);

  const langs = analytics
    ? analytics.by_language.map(l => ({ name: l.language, rate: l.rate, pct: parseFloat(l.rate) }))
    : [];

  const totalRecipients = analytics?.total ?? 0;

  return (
    <div className="page-in w-full">
      <PageHeader
        eyebrow="audience insights"
        title="Audience Insights"
        subtitle={isDemo ? "Demo insights — press Space×5 to switch to live mode." : "Counts only — patterns from your real campaigns."}
        tagline="Listening to the room."
        bubble={isDemo ? "Demo 🎭" : "Patterns, not promises"}
        mascot="girl"
      />

      {loading ? (
        <div style={{ textAlign: "center", padding: "48px", color: "#8A9BB0", fontFamily: "Manrope, sans-serif" }}>Loading insights…</div>
      ) : (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1.5fr) minmax(0,1fr)", gap: "var(--gap)" }}>
            {/* Language distribution */}
            <div className="glass" style={{ padding: "18px 20px" }}>
              <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
                Confirmed rate by language
              </h3>
              {langs.length === 0 ? (
                <p style={{ fontFamily: "Manrope, sans-serif", fontSize: 13, color: "#8A9BB0", margin: 0 }}>No data yet.</p>
              ) : langs.map(l => (
                <div key={l.name} className="hbar">
                  <span>{l.name}</span>
                  <div className="hbar-track"><span className="hbar-fill hbar-fill-y" style={{ width: l.rate }} /></div>
                  <b>{l.rate}</b>
                </div>
              ))}
            </div>

            {/* Follow-up needs */}
            <div className="glass" style={{ padding: "18px 20px" }}>
              <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
                Follow-up needs
              </h3>
              {overview ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {[
                    { label: "Callbacks requested",   val: overview.callbacks_pending },
                    { label: "Eligible for retry",    val: overview.eligible_for_retry },
                    { label: "Calls failed",          val: overview.calls_failed },
                  ].map(row => (
                    <div key={row.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid rgba(23,38,58,.05)" }}>
                      <span style={{ fontFamily: "Manrope, sans-serif", fontSize: 13, color: "#5A6E84" }}>{row.label}</span>
                      <strong style={{ fontFamily: "Manrope, sans-serif", fontSize: 18, color: "#17263A" }}>{row.val ?? "—"}</strong>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ textAlign: "center", padding: "16px 0" }}>
                  <Image src="/veylo-girl.png" alt="" width={72} height={72} style={{ objectFit: "contain", height: "auto", width: "auto" }} />
                  <p style={{ margin: "8px 0 0", fontSize: 13, color: "#4A5B6E" }}>No data yet — launch a campaign.</p>
                </div>
              )}
            </div>
          </div>

          {/* Outcomes by segment */}
          {analytics && (
            <div className="glass" style={{ padding: "18px 20px", marginTop: "var(--gap)" }}>
              <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
                Outcome breakdown — {analytics.campaign_name}
              </h3>
              {Object.entries(analytics.outcomes).map(([key, val]) => {
                const pct = totalRecipients > 0 ? `${((val / totalRecipients) * 100).toFixed(1)}%` : "0%";
                return (
                  <div key={key} style={{ margin: "10px 0" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <b style={{ font: "700 13px 'Manrope'", textTransform: "capitalize" }}>{key.replace(/_/g, " ")}</b>
                      <small style={{ color: "#5B6B7D" }}>{val.toLocaleString()} recipients · {pct}</small>
                    </div>
                    <div className="sbar">
                      <span className="sbar-seg" style={{ width: pct, background: key === "confirmed" ? "var(--ink)" : key === "declined" ? "var(--red)" : "var(--blue)" }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      <div className="pgf"><span>VEYLO / AUDIENCE INSIGHTS</span><i>✳</i></div>
    </div>
  );
}
