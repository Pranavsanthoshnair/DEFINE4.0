import type { Metadata } from "next";
import Link from "next/link";
import PageHeader from "@/components/ui/PageHeader";

export const metadata: Metadata = { title: "Create Campaign — Veylo" };

const STEPS = ["Event", "Contacts", "Language", "Calling", "Review"];

export default function NewCampaignPage() {
  return (
    <div className="page-in" style={{ maxWidth: 1180, margin: "0 auto", padding: "30px 28px 60px" }}>
      <PageHeader
        eyebrow="create campaign"
        title="Create campaign"
        subtitle="Five short steps. Your progress is saved as you go."
        tagline="Begin the invitation."
        bubble="Let's build one!"
        mascot="boy"
      />

      {/* Wizard step bar */}
      <div className="wz">
        {STEPS.map((s, i) => (
          <div key={s} className={`wz-step ${i === 0 ? "active" : ""}`}>
            {i + 1}<span style={{ marginLeft: 4 }}>{s}</span>
          </div>
        ))}
      </div>

      {/* Step 0 — Event details */}
      <div className="glass" style={{ padding: "18px 20px", maxWidth: 600 }}>
        <label style={{ display: "block", font: "700 12px 'Manrope'", marginBottom: 14 }}>
          Campaign name
          <input className="vfield" placeholder="e.g. Onam Cultural Night 2026" style={{ marginTop: 5, fontWeight: 400 }} />
        </label>
        <label style={{ display: "block", font: "700 12px 'Manrope'", marginBottom: 14 }}>
          Event name
          <input className="vfield" placeholder="e.g. Onam Cultural Night" style={{ marginTop: 5, fontWeight: 400 }} />
        </label>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <label style={{ flex: "1 1 180px", font: "700 12px 'Manrope'", marginBottom: 14 }}>
            Event date
            <input type="date" className="vfield" style={{ marginTop: 5, fontWeight: 400 }} />
          </label>
          <label style={{ flex: "1 1 180px", font: "700 12px 'Manrope'", marginBottom: 14 }}>
            City or venue
            <input className="vfield" placeholder="e.g. Kochi" style={{ marginTop: 5, fontWeight: 400 }} />
          </label>
        </div>
      </div>

      {/* Navigation */}
      <div style={{ display: "flex", gap: 10, marginTop: 18 }}>
        <Link href="/campaigns" className="vbtn" style={{ textDecoration: "none", opacity: .45 }}>
          ← BACK
        </Link>
        <button className="vbtn vbtn-ink">NEXT →</button>
      </div>

      <div className="pgf"><span>VEYLO / CREATE CAMPAIGN</span><i>✳</i></div>
    </div>
  );
}
