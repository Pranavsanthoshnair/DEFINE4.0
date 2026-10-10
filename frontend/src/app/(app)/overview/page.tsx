"use client";

import Link from "next/link";
import Image from "next/image";
import { Suspense, useEffect, useState } from "react";
import PageHeader from "@/components/ui/PageHeader";
import Greeting from "@/components/ui/Greeting";
import { useDemo } from "@/context/DemoModeContext";
import { DEMO_OVERVIEW, DEMO_CAMPAIGNS, DEMO_ACTIVITY } from "@/lib/demo-data";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const EMPTY_KPI = [
  { label: "Campaigns",          value: "—"  },
  { label: "Confirmed of total", value: "—%" },
  { label: "Callbacks pending",  value: "—"  },
  { label: "Eligible for retry", value: "—"  },
];

export default function OverviewPage() {
  const { isDemo } = useDemo();
  const [kpi, setKpi] = useState(EMPTY_KPI);
  const [recentCampaigns, setRecentCampaigns] = useState<typeof DEMO_CAMPAIGNS>([]);
  const [activity, setActivity] = useState<typeof DEMO_ACTIVITY>([]);
  const [outcomeData, setOutcomeData] = useState({ confirmed: 0, callback: 0, declined: 0, unanswered: 0, total: 0 });
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");

  useEffect(() => {
    if (isDemo) {
      // Populate entirely from demo-data.ts — no backend calls
      setKpi([
        { label: "Campaigns",          value: String(DEMO_OVERVIEW.campaigns)        },
        { label: "Confirmed of total", value: DEMO_OVERVIEW.confirmed_rate           },
        { label: "Callbacks pending",  value: String(DEMO_OVERVIEW.callbacks_pending) },
        { label: "Eligible for retry", value: String(DEMO_OVERVIEW.eligible_for_retry) },
      ]);
      setRecentCampaigns(DEMO_CAMPAIGNS.slice(0, 3));
      setActivity(DEMO_ACTIVITY);
      setOutcomeData({ confirmed: 2063, callback: 87, declined: 189, unanswered: 64, total: 2450 });
      setBackendStatus("offline");
      return;
    }

    // Live mode — real API only
    setKpi(EMPTY_KPI);
    setRecentCampaigns([]);
    setActivity([]);
    setBackendStatus("checking");

    const controller = new AbortController();

    // Overview summary
    fetch(`${API}/api/overview`, { signal: controller.signal })
      .then((r) => r.ok ? r.json() : Promise.reject(r.status))
      .then((data) => {
        const total = data.total_calls ?? 0;
        const confirmed = data.calls_answered ?? 0;
        const failed = data.calls_failed ?? 0;
        const cb = data.callbacks_pending ?? 0;
        const unanswered = Math.max(0, total - confirmed - failed - cb);
        setKpi([
          { label: "Campaigns",          value: String(data.total_campaigns ?? "—")   },
          { label: "Confirmed of total", value: total > 0 ? `${((confirmed / total) * 100).toFixed(1)}%` : "—%" },
          { label: "Callbacks pending",  value: String(cb)                             },
          { label: "Eligible for retry", value: String(data.eligible_for_retry ?? "—") },
        ]);
        setOutcomeData({ confirmed, callback: cb, declined: failed, unanswered, total });
        setBackendStatus("online");
      })
      .catch((e) => {
        if (e?.name !== "AbortError") setBackendStatus("offline");
      });

    // Recent campaigns
    fetch(`${API}/api/v1/campaigns?limit=3`, { signal: controller.signal })
      .then((r) => r.ok ? r.json() : [])
      .then((data) => setRecentCampaigns(Array.isArray(data) ? data : []))
      .catch(() => {});

    return () => controller.abort();
  }, [isDemo]);

  const pct = (n: number) =>
    outcomeData.total > 0 ? `${((n / outcomeData.total) * 100).toFixed(0)}%` : "0%";

  return (
    <div className="w-full">
      <PageHeader
        eyebrow="overview"
        title={<Suspense fallback="Welcome back"><Greeting suffix="Org" /></Suspense>}
        subtitle={
          isDemo
            ? "Showing demo data — press Space×5 to switch to live mode."
            : backendStatus === "online"
            ? "Live data from your campaigns."
            : "Connect the backend to see live stats."
        }
        tagline="Every voice, invited."
        bubble={isDemo ? "Demo 🎭" : "Welcome back!"}
        mascot="boy"
        action={
          <Link href="/campaigns" className="vbtn vbtn-red" style={{ textDecoration: "none" }}>
            CREATE CAMPAIGN <span>↗</span>
          </Link>
        }
      />

      {/* Backend status pill */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, fontFamily: "Manrope, sans-serif", fontSize: 12 }}>
        <span style={{
          width: 8, height: 8, borderRadius: "50%", display: "inline-block", flexShrink: 0,
          background: isDemo ? "#FFD700" : backendStatus === "online" ? "#22c55e" : backendStatus === "offline" ? "#ef4444" : "#f59e0b",
        }} />
        <span style={{ color: "#8A9BB0", fontWeight: 600 }}>
          {isDemo ? "Demo mode — sample data" : backendStatus === "online" ? "Backend connected" : backendStatus === "offline" ? "Backend offline" : "Connecting…"}
        </span>
        {isDemo && (
          <span style={{ background: "#FFD700", color: "#17263A", fontWeight: 800, fontSize: 10, padding: "2px 8px", borderRadius: 100, letterSpacing: ".06em" }}>
            DEMO
          </span>
        )}
      </div>

      {/* KPI row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(140px,1fr))", gap: "var(--gap)", marginBottom: "var(--gap)" }}>
        {kpi.map((k, i) => (
          <div key={k.label} className="glass" style={{
            padding: "18px 20px",
            background: i === 0 ? "rgba(255,215,0,.86)" : i === 2 ? "rgba(183,216,245,.8)" : undefined,
          }}>
            <span className="kpi-val">{k.value}</span>
            <span className="kpi-lbl">{k.label}</span>
          </div>
        ))}
      </div>

      {/* Content grid */}
      <div className="overview-grid" style={{ display: "grid", gridTemplateColumns: "1fr", gap: "var(--gap)" }}>
        <style>{`@media(min-width:768px){.overview-grid{grid-template-columns:minmax(0,1.5fr) minmax(0,1fr)!important}}`}</style>

        {/* Left */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap)" }}>
          <div className="glass" style={{ padding: "18px 20px" }}>
            <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
              Recent campaigns
            </h3>
            {recentCampaigns.length === 0 ? (
              <div className="em-row">
                <Image src="/veylo-boy.png" alt="" width={96} height={96} style={{ objectFit: "contain", width: "auto", height: "auto" }} />
                <p>No campaigns yet. <Link href="/campaigns" style={{ color: "var(--red)", fontWeight: 600 }}>Create one →</Link></p>
              </div>
            ) : (
              recentCampaigns.map((c) => (
                <div key={c.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid rgba(23,38,58,.06)" }}>
                  <div>
                    <p style={{ margin: 0, fontFamily: "Manrope, sans-serif", fontSize: 13, fontWeight: 700, color: "#17263A" }}>{c.name}</p>
                    <p style={{ margin: 0, fontFamily: "Manrope, sans-serif", fontSize: 11, color: "#8A9BB0" }}>{c.language}</p>
                  </div>
                  <span style={{ fontFamily: "Manrope, sans-serif", fontSize: 12, fontWeight: 700, color: c.status === "running" ? "#16a34a" : c.status === "completed" ? "#64748b" : "#d97706", textTransform: "uppercase", letterSpacing: ".05em" }}>
                    {c.status}
                  </span>
                </div>
              ))
            )}
          </div>

          <div className="glass" style={{ padding: "18px 20px" }}>
            <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
              Needs attention
            </h3>
            <div className="em-row">
              <Image src="/veylo-girl.png" alt="" width={96} height={96} style={{ objectFit: "contain", width: "auto", height: "auto" }} />
              <p>{isDemo ? "47 callbacks pending follow-up." : "Nothing flagged right now."}</p>
            </div>
          </div>
        </div>

        {/* Right */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap)" }}>
          <div className="glass" style={{ padding: "18px 20px" }}>
            <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
              Outcome mix
            </h3>
            <div className="sbar" style={{ marginBottom: 10 }}>
              <span className="sbar-seg" style={{ width: pct(outcomeData.confirmed), background: "var(--ink)" }} />
              <span className="sbar-seg" style={{ width: pct(outcomeData.callback),  background: "var(--blue)" }} />
              <span className="sbar-seg" style={{ width: pct(outcomeData.declined),  background: "var(--red)" }} />
              <span className="sbar-seg" style={{ width: pct(outcomeData.unanswered), background: "rgba(183,216,245,.4)" }} />
            </div>
            {outcomeData.total > 0 ? (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px 16px" }}>
                {[
                  { label: "Confirmed",  n: outcomeData.confirmed,  color: "var(--ink)" },
                  { label: "Callback",   n: outcomeData.callback,   color: "var(--blue)" },
                  { label: "Declined",   n: outcomeData.declined,   color: "var(--red)" },
                  { label: "Unanswered", n: outcomeData.unanswered, color: "rgba(183,216,245,.6)" },
                ].map((s) => (
                  <div key={s.label} style={{ display: "flex", alignItems: "center", gap: 6, fontFamily: "Manrope, sans-serif", fontSize: 11, color: "#5A6E84" }}>
                    <span style={{ width: 8, height: 8, borderRadius: 2, background: s.color, flexShrink: 0 }} />
                    {s.label}: <strong>{s.n.toLocaleString()}</strong>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ fontSize: 12, color: "#8A9BB0", margin: 0 }}>No call data yet.</p>
            )}
          </div>

          <div className="glass" style={{ padding: "18px 20px" }}>
            <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
              Activity
            </h3>
            <div className="tl">
              {activity.length === 0 ? (
                <p className="tl-item" style={{ margin: 0 }}>
                  No activity yet.
                  <small style={{ color: "#5B6B7D", display: "block" }}>Launch a campaign to see events here.</small>
                </p>
              ) : (
                activity.map((e) => (
                  <p key={e.text} className="tl-item" style={{ margin: "0 0 10px" }}>
                    {e.text}
                    <small style={{ color: "#8A9BB0", display: "block" }}>{e.time}</small>
                  </p>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Yellow CTA */}
      <div className="yb" style={{ marginTop: "var(--gap)", flexWrap: "wrap", gap: 16 }}>
        <div>
          <h3>Every call. Every language.</h3>
          <em className="cal">with a human voice</em>
        </div>
        <Image src="/veylo-boy.png" alt="" width={92} height={92} style={{ objectFit: "contain", width: "auto", height: "auto" }} />
        <Link href="/campaigns" className="vbtn vbtn-red" style={{ textDecoration: "none" }}>
          CREATE CAMPAIGN <span>↗</span>
        </Link>
      </div>

      <div className="pgf"><span>VEYLO / OVERVIEW</span><i>✳</i></div>
    </div>
  );
}
