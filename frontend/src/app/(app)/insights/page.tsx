import type { Metadata } from "next";
import Image from "next/image";
import PageHeader from "@/components/ui/PageHeader";

export const metadata: Metadata = { title: "Audience Insights — Veylo" };

const LANGS = ["Malayalam", "English", "Hindi", "Tamil"];
const SEGS  = ["Speakers", "Delegates", "Sponsors", "Volunteers"];

export default function InsightsPage() {
  return (
    <div className="page-in" style={{ maxWidth: 1180, margin: "0 auto", padding: "30px 28px 60px" }}>
      <PageHeader
        eyebrow="audience insights"
        title="Audience Insights"
        subtitle="Counts only. Samples are small — treat patterns as prompts to check, not conclusions."
        tagline="Listening to the room."
        bubble="Patterns, not promises"
        mascot="girl"
      />

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1.5fr) minmax(0,1fr)", gap: "var(--gap)" }}>
        {/* Language distribution */}
        <div className="glass" style={{ padding: "18px 20px" }}>
          <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
            Preferred language
          </h3>
          {LANGS.map((l) => (
            <div key={l} className="hbar">
              <span>{l}</span>
              <div className="hbar-track"><span className="hbar-fill hbar-fill-y" style={{ width: "0%" }} /></div>
              <b>0%</b>
            </div>
          ))}
        </div>

        {/* Follow-up needs */}
        <div className="glass" style={{ padding: "18px 20px" }}>
          <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
            Follow-up needs
          </h3>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, padding: "16px 0" }}>
            <Image src="/veylo-girl.png" alt="" width={72} height={72} style={{ objectFit: "contain" }} />
            <p style={{ margin: 0, fontSize: 13, color: "#4A5B6E", textAlign: "center" }}>
              <b>0</b> callbacks requested<br />
              <b>0</b> unanswered, still retryable<br />
              <b>0</b> opted out<br />
              <b>0</b> numbers to fix
            </p>
          </div>
        </div>
      </div>

      {/* Outcomes by segment */}
      <div className="glass" style={{ padding: "18px 20px", marginTop: "var(--gap)" }}>
        <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
          Outcomes by segment
        </h3>
        {SEGS.map((s) => (
          <div key={s} style={{ margin: "10px 0" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
              <b style={{ font: "700 13px 'Manrope'" }}>{s}</b>
              <small style={{ color: "#5B6B7D" }}>0 recipients</small>
            </div>
            <div className="sbar">
              <span className="sbar-seg" style={{ width: "100%", background: "rgba(183,216,245,.4)" }} />
            </div>
          </div>
        ))}
        <small style={{ color: "#5B6B7D", fontSize: 11 }}>Based on 0 simulated call attempts.</small>
      </div>

      <div className="pgf"><span>VEYLO / AUDIENCE INSIGHTS</span><i>✳</i></div>
    </div>
  );
}
