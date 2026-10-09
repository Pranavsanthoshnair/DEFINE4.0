import type { Metadata } from "next";
import PageHeader from "@/components/ui/PageHeader";

export const metadata: Metadata = { title: "Settings — Veylo" };

export default function SettingsPage() {
  return (
    <div className="page-in" style={{ maxWidth: 1180, margin: "0 auto", padding: "30px 28px 60px" }}>
      <PageHeader
        eyebrow="settings"
        title="Settings"
        subtitle="Defaults for new campaigns."
        tagline="Made to your measure."
        bubble="Tune it your way"
        mascot="boy"
      />

      <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap)", maxWidth: 720 }}>

        {/* Organisation */}
        <div className="glass" style={{ padding: "18px 20px" }}>
          <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 16px", display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
            Organisation
          </h3>
          <label style={{ display: "block", font: "700 12px 'Manrope'", marginBottom: 14 }}>
            Organisation name
            <input className="vfield" defaultValue="Tech Summit Org" style={{ marginTop: 5, fontWeight: 400 }} />
          </label>
          <label style={{ display: "block", font: "700 12px 'Manrope'", marginBottom: 14 }}>
            Time zone
            <select className="vfield" style={{ marginTop: 5, fontWeight: 400 }}>
              {["Asia/Kolkata", "Asia/Dubai", "Europe/London", "America/New_York"].map((z) => (
                <option key={z}>{z}</option>
              ))}
            </select>
          </label>
          <label style={{ display: "block", font: "700 12px 'Manrope'", marginBottom: 14 }}>
            Default language
            <select className="vfield" style={{ marginTop: 5, fontWeight: 400 }}>
              {["English", "Malayalam", "Hindi", "Tamil"].map((l) => (
                <option key={l}>{l}</option>
              ))}
            </select>
          </label>
        </div>

        {/* Calling */}
        <div className="glass" style={{ padding: "18px 20px" }}>
          <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 16px", display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
            Calling
          </h3>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 14 }}>
            <label style={{ flex: "1 1 180px", font: "700 12px 'Manrope'" }}>
              Earliest call
              <input type="time" className="vfield" defaultValue="09:00" style={{ marginTop: 5, fontWeight: 400 }} />
            </label>
            <label style={{ flex: "1 1 180px", font: "700 12px 'Manrope'" }}>
              Latest call
              <input type="time" className="vfield" defaultValue="20:00" style={{ marginTop: 5, fontWeight: 400 }} />
            </label>
            <label style={{ flex: "1 1 180px", font: "700 12px 'Manrope'" }}>
              Default retries
              <input type="number" className="vfield" defaultValue={2} min={0} max={5} style={{ marginTop: 5, fontWeight: 400 }} />
            </label>
            <label style={{ flex: "1 1 180px", font: "700 12px 'Manrope'" }}>
              Hours between attempts
              <input type="number" className="vfield" defaultValue={4} min={1} max={48} style={{ marginTop: 5, fontWeight: 400 }} />
            </label>
          </div>
        </div>

        {/* Privacy */}
        <div className="glass" style={{ padding: "18px 20px" }}>
          <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 16px", display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
            Privacy
          </h3>
          <label style={{ display: "block", font: "700 12px 'Manrope'", marginBottom: 14 }}>
            Keep call records for (days)
            <input type="number" className="vfield" defaultValue={90} style={{ marginTop: 5, fontWeight: 400 }} />
          </label>
          <p style={{ fontSize: 12, color: "#5B6B7D", margin: 0 }}>
            Contacts marked as not allowed to receive calls are never dialled.
          </p>
        </div>

        {/* Exotel integration */}
        <div className="glass" style={{ padding: "18px 20px" }}>
          <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
            Exotel integration
          </h3>
          <p style={{ margin: "0 0 8px" }}>
            <span className="vchip" style={{ background: "var(--yellow)", borderStyle: "dashed" }}>Not configured</span>
            {" "}Running in demo mode.
          </p>
          <p style={{ fontSize: 12, color: "#5B6B7D", margin: 0 }}>
            API keys are never stored in the browser. Add them to your server environment and route
            provider webhooks through it with signature checks.
          </p>
        </div>

        <button className="vbtn vbtn-red" style={{ alignSelf: "flex-start" }}>
          SAVE SETTINGS
        </button>
      </div>

      <div className="pgf"><span>VEYLO / SETTINGS</span><i>✳</i></div>
    </div>
  );
}
