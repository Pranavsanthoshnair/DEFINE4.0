import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import PageHeader from "@/components/ui/PageHeader";

export const metadata: Metadata = { title: "Campaign Detail — Veylo" };

export default function CampaignDetailPage({ params }: { params: { id: string } }) {
  return (
    <div className="page-in" style={{ maxWidth: 1180, margin: "0 auto", padding: "30px 28px 60px" }}>
      <PageHeader
        eyebrow="campaign detail"
        title={`Campaign #${params.id}`}
        subtitle="Connect the backend to see live campaign data."
        tagline="The story of a campaign."
        bubble="Ring ring!"
        mascot="boy"
        action={
          <Link href="/campaigns" className="vbtn" style={{ textDecoration: "none" }}>
            ← Back to campaigns
          </Link>
        }
      />

      {/* Progress bar placeholder */}
      <div className="glass" style={{ padding: "18px 20px", marginBottom: "var(--gap)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", font: "700 13px 'Manrope'", marginBottom: 8 }}>
          <span>Call progress</span>
          <span>0 / 0</span>
        </div>
        <div className="sbar">
          <span className="sbar-seg" style={{ width: "100%", background: "rgba(183,216,245,.4)" }} />
        </div>
      </div>

      {/* KPI row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(130px,1fr))", gap: "var(--gap)", marginBottom: "var(--gap)" }}>
        {[
          { label: "Confirmed",          v: "—" },
          { label: "Declined",           v: "—" },
          { label: "Unanswered",         v: "—", yellow: true },
          { label: "Callback requested", v: "—", blue: true },
        ].map((k, i) => (
          <div key={k.label} className="glass" style={{
            padding: "18px 20px",
            background: i === 2 ? "rgba(255,215,0,.86)" : i === 3 ? "rgba(183,216,245,.8)" : undefined,
          }}>
            <span className="kpi-val">{k.v}</span>
            <span className="kpi-lbl">{k.label}</span>
          </div>
        ))}
      </div>

      {/* Two-column body */}
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1.5fr) minmax(0,1fr)", gap: "var(--gap)" }}>
        <div className="glass" style={{ padding: "18px 20px" }}>
          <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
            Recipients
          </h3>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, padding: "24px 0" }}>
            <Image src="/veylo-girl.png" alt="" width={80} height={80} style={{ objectFit: "contain" }} />
            <p style={{ margin: 0, font: "600 14px 'Manrope'", color: "#4A5B6E" }}>
              No recipients data yet.
            </p>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap)" }}>
          <div className="glass" style={{ padding: "18px 20px" }}>
            <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
              By language
            </h3>
            {["Malayalam", "English", "Hindi", "Tamil"].map((l) => (
              <div key={l} className="hbar">
                <span>{l}</span>
                <div className="hbar-track"><span className="hbar-fill hbar-fill-y" style={{ width: "0%" }} /></div>
                <b>0%</b>
              </div>
            ))}
            <small style={{ color: "#5B6B7D", fontSize: 11 }}>Share confirmed per language</small>
          </div>

          <div className="glass" style={{ padding: "18px 20px" }}>
            <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
              Timeline
            </h3>
            <div className="tl">
              <p className="tl-item" style={{ margin: 0 }}>
                No activity yet.
                <small style={{ color: "#5B6B7D", display: "block" }}>Connect backend to see events.</small>
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="pgf"><span>VEYLO / CAMPAIGN DETAIL</span><i>✳</i></div>
    </div>
  );
}
