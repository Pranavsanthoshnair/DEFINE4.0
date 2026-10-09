"use client";

import PageHeader from "@/components/ui/PageHeader";
import { useDemo } from "@/context/DemoModeContext";

const DEMO_MEMBERS = [
  { name: "Nisha Thomas",  email: "nisha@techsummit.org",  role: "Admin" },
  { name: "Arjun Pillai",  email: "arjun@techsummit.org",  role: "Campaign manager" },
  { name: "Mira Das",      email: "mira@techsummit.org",   role: "Viewer" },
];

const ROLES = ["Admin", "Campaign manager", "Viewer"];
const ROLE_DESC: Record<string, string> = {
  Admin:              "Everything, including team and settings",
  "Campaign manager": "Create, launch and retry campaigns; manage contacts",
  Viewer:             "View campaigns and analytics only",
};

export default function TeamPage() {
  const { isDemo } = useDemo();
  const members = isDemo ? DEMO_MEMBERS : [];

  return (
    <div className="page-in" style={{ maxWidth: 1180, margin: "0 auto", padding: "30px 28px 60px" }}>
      <PageHeader
        eyebrow="team & permissions"
        title="Team & Permissions"
        subtitle={isDemo ? "Demo mode — showing sample team." : "Roles decide who can launch calls and see contact data."}
        tagline="Hands that share the work."
        bubble={isDemo ? "Demo 🎭" : "Your team"}
        mascot="girl"
      />

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1.5fr) minmax(0,1fr)", gap: "var(--gap)" }}>
        {/* Members table */}
        <div className="glass" style={{ padding: "18px 20px" }}>
          <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
            Members
          </h3>
          {members.length === 0 ? (
            <p style={{ fontFamily: "Manrope, sans-serif", fontSize: 13, color: "#8A9BB0", margin: 0 }}>
              No team members yet. Invite someone using the form →
            </p>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table className="vtable">
                <tbody>
                  {members.map((m) => (
                    <tr key={m.email}>
                      <td>
                        <b style={{ font: "700 13px 'Manrope'" }}>{m.name}</b>
                        <br />
                        <small style={{ color: "#5B6B7D" }}>{m.email}</small>
                      </td>
                      <td>
                        <span className="vchip vchip-callback">{m.role}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Right stack */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap)" }}>
          {/* Invite form */}
          <div className="glass" style={{ padding: "18px 20px" }}>
            <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
              Invite someone
            </h3>
            <label style={{ display: "block", font: "700 12px 'Manrope'", marginBottom: 14 }}>
              Email
              <input type="email" className="vfield" style={{ marginTop: 5, fontWeight: 400 }} placeholder="colleague@yourorg.com" />
            </label>
            <label style={{ display: "block", font: "700 12px 'Manrope'", marginBottom: 14 }}>
              Role
              <select className="vfield" style={{ marginTop: 5, fontWeight: 400, appearance: "none" }}>
                {ROLES.map((r) => <option key={r}>{r}</option>)}
              </select>
            </label>
            <button className="vbtn vbtn-sm vbtn-ink" disabled style={{ opacity: .5, cursor: "not-allowed" }}>
              ADD INVITATION
            </button>
            <p style={{ fontSize: 12, color: "#5B6B7D", marginTop: 8 }}>
              Invitation emails are not sent until an email service is connected.
            </p>
          </div>

          {/* Role descriptions */}
          <div className="glass" style={{ padding: "18px 20px" }}>
            <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
              What each role can do
            </h3>
            {ROLES.map((r) => (
              <p key={r} style={{ margin: "0 0 8px" }}>
                <b style={{ font: "700 13px 'Manrope'" }}>{r}</b>
                <br />
                <small style={{ color: "#5B6B7D" }}>{ROLE_DESC[r]}</small>
              </p>
            ))}
          </div>
        </div>
      </div>

      <div className="pgf"><span>VEYLO / TEAM & PERMISSIONS</span><i>✳</i></div>
    </div>
  );
}
