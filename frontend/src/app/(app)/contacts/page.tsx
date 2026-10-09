import type { Metadata } from "next";
import Image from "next/image";
import PageHeader from "@/components/ui/PageHeader";

export const metadata: Metadata = { title: "Contacts — Veylo" };

export default function ContactsPage() {
  return (
    <div className="page-in" style={{ maxWidth: 1180, margin: "0 auto", padding: "30px 28px 60px" }}>
      <PageHeader
        eyebrow="contacts"
        title="Contacts"
        subtitle="Import and manage your recipients. Duplicates and invalid numbers are flagged automatically."
        tagline="Know your guests."
        bubble="Mind the duplicates!"
        mascot="girl"
        action={
          <button className="vbtn vbtn-ink" disabled style={{ opacity: .5, cursor: "not-allowed" }}>
            ADD CONTACT
          </button>
        }
      />

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1.5fr) minmax(0,1fr)", gap: "var(--gap)" }}>
        {/* Contacts table */}
        <div className="glass" style={{ padding: "18px 20px" }}>
          <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
            All contacts
          </h3>
          <div style={{ overflowX: "auto" }}>
            <table className="vtable">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Language</th>
                  <th>Segment</th>
                  <th>Calls allowed</th>
                  <th>Flags</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td colSpan={5} style={{ textAlign: "center", paddingTop: 32, paddingBottom: 32 }}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
                      <Image src="/veylo-girl.png" alt="" width={80} height={80} style={{ objectFit: "contain" }} />
                      <p style={{ margin: 0, font: "600 14px 'Manrope'", color: "#4A5B6E" }}>
                        No contacts yet. Import a CSV to get started.
                      </p>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* CSV import panel */}
        <div className="glass" style={{ padding: "18px 20px" }}>
          <h3 style={{ font: "800 17px 'Manrope'", letterSpacing: "-.03em", margin: "0 0 12px", display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }} />
            Import CSV
          </h3>
          <p style={{ fontSize: 13, margin: "0 0 12px", color: "#4A5B6E" }}>
            Columns: <code>name</code>, <code>phone</code>, <code>language</code>, <code>segment</code>.
          </p>

          <label style={{ display: "block", font: "700 12px 'Manrope'", marginBottom: 14 }}>
            Upload file
            <input
              type="file"
              accept=".csv,text/csv"
              className="vfield"
              style={{ marginTop: 5, fontWeight: 400, cursor: "pointer" }}
              aria-label="CSV file"
            />
          </label>

          <label style={{ display: "block", font: "700 12px 'Manrope'", marginBottom: 14 }}>
            Or paste rows
            <textarea
              className="vfield"
              placeholder="Anjali Nair,+91 9876543210,Malayalam,Speakers"
              style={{ marginTop: 5, fontWeight: 400 }}
            />
          </label>

          <button className="vbtn vbtn-sm vbtn-ink" disabled style={{ opacity: .5, cursor: "not-allowed" }}>
            VALIDATE
          </button>

          <p style={{ fontSize: 12, color: "#5B6B7D", marginTop: 10 }}>
            CSV import is live once the backend is connected.
          </p>
        </div>
      </div>

      <div className="pgf"><span>VEYLO / CONTACTS</span><i>✳</i></div>
    </div>
  );
}
