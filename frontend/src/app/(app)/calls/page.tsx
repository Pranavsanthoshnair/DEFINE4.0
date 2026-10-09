import type { Metadata } from "next";
import Image from "next/image";
import PageHeader from "@/components/ui/PageHeader";

export const metadata: Metadata = { title: "Call History — Veylo" };

export default function CallsPage() {
  return (
    <div className="page-in" style={{ maxWidth: 1180, margin: "0 auto", padding: "30px 28px 60px" }}>
      <PageHeader
        eyebrow="call history"
        title="Call History"
        subtitle="Every call attempt, with its outcome and duration."
        tagline="Every ring, remembered."
        bubble="Every ring, remembered"
        mascot="boy"
      />

      <div className="glass" style={{ padding: "18px 20px", overflowX: "auto" }}>
        <table className="vtable">
          <thead>
            <tr>
              <th>When</th>
              <th>Contact</th>
              <th>Campaign</th>
              <th>Attempt</th>
              <th>Status</th>
              <th>Duration</th>
              <th>Recording</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={7} style={{ textAlign: "center", paddingTop: 32, paddingBottom: 32 }}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
                  <Image src="/veylo-boy.png" alt="" width={80} height={80} style={{ objectFit: "contain" }} />
                  <p style={{ margin: 0, font: "600 14px 'Manrope'", color: "#4A5B6E" }}>
                    No calls yet. Launch a campaign to see history here.
                  </p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="pgf"><span>VEYLO / CALL HISTORY</span><i>✳</i></div>
    </div>
  );
}
