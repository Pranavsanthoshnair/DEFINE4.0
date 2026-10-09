import type { Metadata } from "next";
import Image from "next/image";
import PageHeader from "@/components/ui/PageHeader";

export const metadata: Metadata = { title: "Analytics — Veylo" };

const METRICS = [
  { label: "Answer rate",              value: "—%", yellow: true  },
  { label: "Confirmed among answered", value: "—%", yellow: false },
  { label: "Retry success rate",       value: "—%", blue: true    },
];

export default function AnalyticsPage() {
  return (
    <div className="page-in" style={{ maxWidth: 1180, margin: "0 auto", padding: "30px 28px 60px" }}>
      <PageHeader
        eyebrow="analytics"
        title="Analytics"
        subtitle="Campaign performance and recipient-level call history. Live results appear once calling is connected."
        tagline="Reach, measured."
        bubble="Numbers look good!"
        mascot="girl"
      />

      {/* KPI row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))", gap: "var(--gap)", marginBottom: "var(--gap)" }}>
        {METRICS.map((m, i) => (
          <div
            key={m.label}
            className="glass"
            style={{
              padding: "18px 20px",
              background: i === 0 ? "rgba(255,215,0,.86)" : i === 2 ? "rgba(183,216,245,.8)" : undefined,
            }}
          >
            <span className="kpi-val">{m.value}</span>
            <span className="kpi-lbl">{m.label}</span>
          </div>
        ))}
      </div>

      {/* Charts area */}
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1.5fr) minmax(0,1fr)", gap: "var(--gap)" }}>
        <div className="glass" style={{ padding: "18px 20px" }}>
          <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 14px", display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
            Confirmed rate by campaign
          </h3>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "32px 0", gap: 12 }}>
            <Image src="/veylo-girl.png" alt="" width={80} height={80} style={{ objectFit: "contain" }} />
            <p style={{ margin: 0, fontSize: 13, color: "#4A5B6E" }}>Charts will appear here once campaigns are active.</p>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap)" }}>
          <div className="glass" style={{ padding: "18px 20px" }}>
            <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
              Answer rate by language
            </h3>
            {["Malayalam", "English", "Hindi", "Tamil"].map((lang) => (
              <div key={lang} className="hbar">
                <span>{lang}</span>
                <div className="hbar-track"><span className="hbar-fill hbar-fill-y" style={{ width: "0%" }} /></div>
                <b>0%</b>
              </div>
            ))}
          </div>

          <div className="glass" style={{ padding: "18px 20px" }}>
            <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
              Confirmed by segment
            </h3>
            {["Speakers", "Delegates", "Sponsors", "Volunteers"].map((seg) => (
              <div key={seg} className="hbar">
                <span>{seg}</span>
                <div className="hbar-track"><span className="hbar-fill" style={{ width: "0%" }} /></div>
                <b>0%</b>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="pgf"><span>VEYLO / ANALYTICS</span><i>✳</i></div>
    </div>
  );
}
