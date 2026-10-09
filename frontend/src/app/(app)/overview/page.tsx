import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import { Suspense } from "react";
import PageHeader from "@/components/ui/PageHeader";
import Greeting from "@/components/ui/Greeting";

export const metadata: Metadata = { title: "Overview — Veylo" };

const KPI = [
  { label: "Campaigns",          value: "—" },
  { label: "Confirmed of total", value: "—%" },
  { label: "Callbacks pending",  value: "—" },
  { label: "Eligible for retry", value: "—" },
];

export default function OverviewPage() {
  return (
    <div className="page-in" style={{ maxWidth: 1180, margin: "0 auto", padding: "30px 28px 60px" }}>
      <PageHeader
        eyebrow="overview"
        title={<Suspense fallback="Welcome back"><Greeting suffix="Org" /></Suspense>}
        subtitle="Here is where your invitations stand. Connect the backend to see live data."
        tagline="Every voice, invited."
        bubble="Welcome back!"
        mascot="boy"
        action={
          <Link href="/campaigns" className="vbtn vbtn-red" style={{ textDecoration: "none" }}>
            CREATE CAMPAIGN <span>↗</span>
          </Link>
        }
      />

      {/* KPI row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))", gap: "var(--gap)", marginBottom: "var(--gap)" }}>
        {KPI.map((k, i) => (
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

      {/* Two-column content */}
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1.5fr) minmax(0,1fr)", gap: "var(--gap)" }}>
        {/* Left stack */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap)" }}>
          <div className="glass" style={{ padding: "18px 20px" }}>
            <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
              Needs your attention
            </h3>
            {/* Empty state with girl mascot */}
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
            <div className="em-row">
              <Image src="/veylo-boy.png" alt="" width={96} height={96} style={{ objectFit: "contain" }} />
              <p>No campaigns yet. <Link href="/campaigns" style={{ color: "var(--red)", fontWeight: 600 }}>Create one</Link>.</p>
            </div>
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
              <span className="sbar-seg" style={{ width: "0%", background: "var(--ink)" }} />
              <span className="sbar-seg" style={{ width: "0%", background: "var(--blue)" }} />
              <span className="sbar-seg" style={{ width: "0%", background: "var(--red)" }} />
              <span className="sbar-seg" style={{ width: "100%", background: "rgba(183,216,245,.4)" }} />
            </div>
            <p style={{ fontSize: 12, color: "#4A5B6E", margin: 0 }}>Confirmed · callback · declined · unanswered</p>
          </div>

          <div className="glass" style={{ padding: "18px 20px" }}>
            <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
              Activity
            </h3>
            <div className="tl">
              <p className="tl-item" style={{ margin: 0 }}>No activity yet.<small style={{ color: "#5B6B7D", display: "block" }}>Launch a campaign to see events here.</small></p>
            </div>
          </div>
        </div>
      </div>

      {/* Yellow CTA banner */}
      <div className="yb" style={{ marginTop: "var(--gap)" }}>
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
