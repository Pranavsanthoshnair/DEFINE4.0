"use client";

import Link from "next/link";
import Image from "next/image";
import { Suspense, useEffect, useState } from "react";
import PageHeader from "@/components/ui/PageHeader";
import Greeting from "@/components/ui/Greeting";
import { useDemo } from "@/context/DemoModeContext";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const DEMO_KPI = [
  { label: "Campaigns",          value: "12"    },
  { label: "Confirmed of total", value: "84.2%" },
  { label: "Callbacks pending",  value: "47"    },
  { label: "Eligible for retry", value: "133"   },
];

const EMPTY_KPI = [
  { label: "Campaigns",          value: "—"  },
  { label: "Confirmed of total", value: "—%" },
  { label: "Callbacks pending",  value: "—"  },
  { label: "Eligible for retry", value: "—"  },
];

export default function OverviewPage() {
  const { isDemo } = useDemo();
  const [kpi, setKpi] = useState(EMPTY_KPI);
  const [backendStatus, setBackendStatus] = useState<"checking"|"online"|"offline">("checking");

  // Fetch real KPIs from backend
  useEffect(() => {
    if (isDemo) {
      setKpi(DEMO_KPI);
      setBackendStatus("offline");
      return;
    }
    setKpi(EMPTY_KPI);
    setBackendStatus("checking");

    fetch(`${API}/api/overview/`)
      .then((r) => r.ok ? r.json() : Promise.reject(r.status))
      .then((data) => {
        setKpi([
          { label: "Campaigns",          value: String(data.campaigns ?? "—")        },
          { label: "Confirmed of total", value: data.confirmed_rate ?? "—%"           },
          { label: "Callbacks pending",  value: String(data.callbacks_pending ?? "—") },
          { label: "Eligible for retry", value: String(data.eligible_retry ?? "—")   },
        ]);
        setBackendStatus("online");
      })
      .catch(() => setBackendStatus("offline"));
  }, [isDemo]);

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto" }}>
      <PageHeader
        eyebrow="overview"
        title={<Suspense fallback="Welcome back"><Greeting suffix="Org" /></Suspense>}
        subtitle={
          backendStatus === "online"
            ? "Live data from your campaigns."
            : backendStatus === "offline" && !isDemo
            ? "Connect the backend to see live data."
            : "Showing demo data — press Space×5 to switch."
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
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: backendStatus === "online" ? "#22c55e" : backendStatus === "offline" ? "#ef4444" : "#f59e0b", display: "inline-block", animation: backendStatus === "checking" ? "pulseRing 1s infinite" : "none" }} />
        <span style={{ color: "#8A9BB0", fontWeight: 600 }}>
          {backendStatus === "online" ? "Backend connected" : backendStatus === "offline" ? (isDemo ? "Demo mode active" : "Backend offline") : "Connecting…"}
        </span>
        {isDemo && <span style={{ background: "#FFD700", color: "#17263A", fontWeight: 800, fontSize: 10, padding: "2px 8px", borderRadius: 100, letterSpacing: ".06em" }}>DEMO</span>}
      </div>

      {/* KPI row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(140px,1fr))", gap: "var(--gap)", marginBottom: "var(--gap)" }}>
        {kpi.map((k, i) => (
          <div
            key={k.label}
            className="glass"
            style={{
              padding: "18px 20px",
              background: i === 0 ? "rgba(255,215,0,.86)" : i === 2 ? "rgba(183,216,245,.8)" : undefined,
              transition: "transform .18s",
              cursor: "default",
            }}
          >
            <span className="kpi-val">{k.value}</span>
            <span className="kpi-lbl">{k.label}</span>
          </div>
        ))}
      </div>

      {/* Content grid — stacks on mobile, 2-col on md+ */}
      <div className="overview-grid" style={{ display: "grid", gridTemplateColumns: "1fr", gap: "var(--gap)" }}>
        <style>{`@media(min-width:768px){.overview-grid{grid-template-columns:minmax(0,1.5fr) minmax(0,1fr)!important}}`}</style>
        {/* Left stack */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap)" }}>
          <div className="glass" style={{ padding: "18px 20px" }}>
            <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
              Needs your attention
            </h3>
            <div className="em-row">
              <Image src="/veylo-girl.png" alt="" width={96} height={96} style={{ objectFit: "contain", width: "auto", height: 96 }} />
              <p>Nothing needs follow-up right now.</p>
            </div>
          </div>

          <div className="glass" style={{ padding: "18px 20px" }}>
            <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
              Recent campaigns
            </h3>
            {isDemo ? (
              [
                { name: "Annual Tech Summit 2026 VIP Invite", status: "running", rate: "84.2%" },
                { name: "Keynote RSVP Confirmation Wave 1",  status: "completed", rate: "91.8%" },
              ].map((c) => (
                <div key={c.name} className="em-row" style={{ justifyContent: "space-between", paddingBottom: 8, borderBottom: "1px solid rgba(23,38,58,.06)" }}>
                  <span style={{ fontFamily: "Manrope, sans-serif", fontSize: 13, fontWeight: 600, color: "#17263A" }}>{c.name}</span>
                  <span style={{ fontFamily: "Manrope, sans-serif", fontSize: 12, fontWeight: 700, color: c.status === "running" ? "#16a34a" : "#8A9BB0" }}>{c.rate}</span>
                </div>
              ))
            ) : (
              <div className="em-row">
                <Image src="/veylo-boy.png" alt="" width={96} height={96} style={{ objectFit: "contain" }} />
                <p>No campaigns yet. <Link href="/campaigns" style={{ color: "var(--red)", fontWeight: 600 }}>Create one</Link>.</p>
              </div>
            )}
          </div>
        </div>

        {/* Right stack */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap)" }}>
          <div className="glass" style={{ padding: "18px 20px" }}>
            <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
              Outcome mix
            </h3>
            <div className="sbar" style={{ marginBottom: 8 }}>
              <span className="sbar-seg" style={{ width: isDemo ? "42%" : "0%", background: "var(--ink)" }} />
              <span className="sbar-seg" style={{ width: isDemo ? "18%" : "0%", background: "var(--blue)" }} />
              <span className="sbar-seg" style={{ width: isDemo ? "8%" : "0%",  background: "var(--red)" }} />
              <span className="sbar-seg" style={{ width: isDemo ? "32%" : "100%", background: "rgba(183,216,245,.4)" }} />
            </div>
            <p style={{ fontSize: 12, color: "#4A5B6E", margin: 0 }}>Confirmed · Callback · Declined · Unanswered</p>
          </div>

          <div className="glass" style={{ padding: "18px 20px" }}>
            <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
              Activity
            </h3>
            <div className="tl">
              {isDemo ? (
                [
                  { text: "Campaign launched — Annual Tech Summit", time: "2h ago" },
                  { text: "1,200 contacts confirmed",                time: "4h ago" },
                  { text: "CSV imported — 2,450 contacts",          time: "6h ago" },
                ].map((e) => (
                  <p key={e.text} className="tl-item" style={{ margin: "0 0 8px" }}>
                    {e.text}
                    <small style={{ color: "#8A9BB0", display: "block" }}>{e.time}</small>
                  </p>
                ))
              ) : (
                <p className="tl-item" style={{ margin: 0 }}>
                  No activity yet.
                  <small style={{ color: "#5B6B7D", display: "block" }}>Launch a campaign to see events here.</small>
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Yellow CTA banner */}
      <div className="yb" style={{ marginTop: "var(--gap)", flexWrap: "wrap", gap: 16 }}>
        <div>
          <h3>Every call. Every language.</h3>
          <em className="cal">with a human voice</em>
        </div>
        <Image src="/veylo-boy.png" alt="" width={92} height={92} style={{ objectFit: "contain" }} />
        <Link href="/campaigns" className="vbtn vbtn-red" style={{ textDecoration: "none" }}>
          CREATE CAMPAIGN <span>↗</span>
        </Link>
      </div>

      <div className="pgf">
        <span>VEYLO / OVERVIEW</span>
        <i>✳</i>
      </div>
    </div>
  );
}
