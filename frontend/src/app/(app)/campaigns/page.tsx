import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import PageHeader from "@/components/ui/PageHeader";

export const metadata: Metadata = { title: "Campaigns — Veylo" };

const STATUSES = ["All", "Draft", "Scheduled", "Running", "Completed", "Failed"];

export default function CampaignsPage() {
  return (
    <div className="page-in" style={{ maxWidth: 1180, margin: "0 auto", padding: "30px 28px 60px" }}>
      <PageHeader
        eyebrow="campaigns"
        title="Campaigns"
        subtitle="Every invitation run, with its status and response rate."
        tagline="One call, every language."
        bubble="Let's invite everyone!"
        mascot="boy"
        action={
          <Link href="/campaigns/new" className="vbtn vbtn-red" style={{ textDecoration: "none" }}>
            NEW CAMPAIGN <span>↗</span>
          </Link>
        }
      />

      {/* Filter tabs */}
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
        {STATUSES.map((s, i) => (
          <button
            key={s}
            className="vbtn vbtn-sm"
            style={{
              background: i === 0 ? "var(--ink)" : "var(--white)",
              color: i === 0 ? "var(--white)" : "var(--ink)",
              border: "1.5px solid var(--ink)",
            }}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Table / empty state */}
      <div className="glass" style={{ padding: "18px 20px", overflowX: "auto" }}>
        <table className="vtable">
          <thead>
            <tr>
              <th>Campaign</th>
              <th>Status</th>
              <th>Recipients</th>
              <th>Confirmed</th>
              <th>Answered</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={6} style={{ textAlign: "center", paddingTop: 32, paddingBottom: 32 }}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
                  <Image src="/veylo-boy.png" alt="" width={80} height={80} style={{ objectFit: "contain" }} />
                  <p style={{ margin: 0, font: "600 14px 'Manrope'", color: "#4A5B6E" }}>
                    No campaigns yet. <Link href="/campaigns/new" style={{ color: "var(--red)", fontWeight: 600 }}>Create one ↗</Link>
                  </p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="pgf"><span>VEYLO / CAMPAIGNS</span><i>✳</i></div>
    </div>
  );
}
