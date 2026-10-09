"use client";

import Image from "next/image";
import PageHeader from "@/components/ui/PageHeader";
import { useDemo } from "@/context/DemoModeContext";
import { DEMO_ANALYTICS } from "@/lib/demo-data";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function AnalyticsPage() {
  const { isDemo } = useDemo();
  const [data, setData] = useState<typeof DEMO_ANALYTICS | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isDemo) { setData(DEMO_ANALYTICS); setLoading(false); return; }
    // Live: fetch analytics for most recent campaign
    setLoading(true);
    fetch(`${API}/api/v1/campaigns/?limit=1`)
      .then(r => r.ok ? r.json() : [])
      .then(async (camps: {id:string}[]) => {
        if (!camps.length) { setData(null); setLoading(false); return; }
        const id = camps[0].id;
        const r = await fetch(`${API}/api/v1/analytics/${id}`);
        if (r.ok) { const d = await r.json(); setData(d); }
        else { setData(null); }
      })
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [isDemo]);

  const total = data?.total ?? 0;
  const pct = (n: number) => total > 0 ? `${((n / total) * 100).toFixed(1)}%` : "0%";
  const metrics = [
    { label: "Answer rate",              value: total > 0 ? pct((data?.outcomes?.confirmed ?? 0) + (data?.outcomes?.declined ?? 0) + (data?.outcomes?.call_later ?? 0)) : "—%" },
    { label: "Confirmed among answered", value: total > 0 ? pct(data?.outcomes?.confirmed ?? 0) : "—%" },
    { label: "Retry success rate",       value: data ? "—%" : "—%" },
  ];

  return (
    <div className="page-in" style={{ maxWidth: 1180, margin: "0 auto", padding: "30px 28px 60px" }}>
      <PageHeader
        eyebrow="analytics"
        title="Analytics"
        subtitle={isDemo ? "Demo data — press Space×5 to switch to live mode." : "Live campaign performance."}
        tagline="Reach, measured."
        bubble={isDemo ? "Demo 🎭" : "Numbers!"}
        mascot="girl"
      />

      {/* KPI row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))", gap: "var(--gap)", marginBottom: "var(--gap)" }}>
        {metrics.map((m, i) => (
          <div key={m.label} className="glass" style={{ padding: "18px 20px", background: i === 0 ? "rgba(255,215,0,.86)" : i === 2 ? "rgba(183,216,245,.8)" : undefined }}>
            <span className="kpi-val">{m.value}</span>
            <span className="kpi-lbl">{m.label}</span>
          </div>
        ))}
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: "48px", color: "#8A9BB0", fontFamily: "Manrope, sans-serif" }}>Loading analytics…</div>
      ) : !data ? (
        <div className="glass" style={{ padding: "48px 24px", textAlign: "center" }}>
          <Image src="/veylo-girl.png" alt="" width={80} height={80} style={{ objectFit: "contain", height: "auto", width: "auto" }} />
          <p style={{ margin: "12px 0 0", fontFamily: "Manrope, sans-serif", fontSize: 14, color: "#5A6E84" }}>
            No analytics yet — launch a campaign and results will appear here.
          </p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1.5fr) minmax(0,1fr)", gap: "var(--gap)" }}>
          {/* Outcome breakdown */}
          <div className="glass" style={{ padding: "18px 20px" }}>
            <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 16px", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
              Outcomes — {data.campaign_name}
            </h3>
            {Object.entries(data.outcomes ?? {}).map(([key, val]) => (
              <div key={key} className="hbar">
                <span style={{ textTransform: "capitalize" }}>{key.replace(/_/g, " ")}</span>
                <div className="hbar-track">
                  <span className="hbar-fill" style={{ width: pct(val as number), background: key === "confirmed" ? "var(--ink)" : key === "declined" ? "var(--red)" : "var(--blue)" }} />
                </div>
                <b>{pct(val as number)}</b>
              </div>
            ))}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap)" }}>
            {/* By language */}
            <div className="glass" style={{ padding: "18px 20px" }}>
              <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
                Confirmed by language
              </h3>
              {(data.by_language ?? []).map((l) => (
                <div key={l.language} className="hbar">
                  <span>{l.language}</span>
                  <div className="hbar-track"><span className="hbar-fill hbar-fill-y" style={{ width: l.rate }} /></div>
                  <b>{l.rate}</b>
                </div>
              ))}
            </div>

            {/* Daily trend */}
            <div className="glass" style={{ padding: "18px 20px" }}>
              <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
                Daily calls
              </h3>
              {(data.by_day ?? []).map((d) => (
                <div key={d.date} className="hbar">
                  <span>{d.date}</span>
                  <div className="hbar-track"><span className="hbar-fill" style={{ width: `${((d.confirmed / d.calls) * 100).toFixed(0)}%` }} /></div>
                  <b>{d.confirmed}/{d.calls}</b>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="pgf"><span>VEYLO / ANALYTICS</span><i>✳</i></div>
    </div>
  );
}
