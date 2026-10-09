import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy & Data Policy — Veylo",
  description:
    "How Veylo processes personal data for outbound calling campaigns: storage location, retention periods, encryption, and your rights.",
};

export default function PrivacyPage() {
  return (
    <div
      style={{
        maxWidth: 760,
        margin: "60px auto",
        padding: "0 28px 80px",
        font: "400 15px/1.7 'DM Sans', 'Manrope', sans-serif",
        color: "var(--ink)",
      }}
    >
      <p
        style={{
          font: "700 11px 'Manrope'",
          letterSpacing: ".12em",
          textTransform: "uppercase",
          color: "var(--red)",
          marginBottom: 10,
        }}
      >
        Legal / Privacy
      </p>
      <h1
        style={{
          font: "800 38px/1.1 'Manrope'",
          letterSpacing: "-.04em",
          marginBottom: 8,
        }}
      >
        Privacy &amp; Data Policy
      </h1>
      <p style={{ color: "#5B6B7D", marginBottom: 40, fontSize: 13 }}>
        Last updated: October 2026 &nbsp;·&nbsp; Veylo — PR 002
      </p>

      {/* ── Overview ─────────────────────────────────────────────────────── */}
      <Section title="1. What Veylo Does">
        <p>
          Veylo is an AI-assisted outbound calling platform that helps
          organisations send multilingual voice invitations to event attendees.
          It is used by institution administrators (&quot;organisers&quot;) who
          upload a list of contacts and launch automated calls. Veylo never
          initiates calls without explicit human authorisation from an
          authenticated organiser.
        </p>
      </Section>

      {/* ── Data collected ───────────────────────────────────────────────── */}
      <Section title="2. Personal Data We Process">
        <table style={tableStyle}>
          <thead>
            <tr>
              {["Data element", "Source", "Purpose", "Stored?"].map((h) => (
                <th key={h} style={thStyle}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[
              ["Phone number", "CSV upload by organiser", "Place the call", "Encrypted (AES-256-GCM); only last 4 digits in logs"],
              ["Contact name", "CSV upload", "None — not spoken or logged", "Encrypted; never sent to AI service"],
              ["Language preference", "CSV upload", "Select TTS voice and STT model", "Plaintext"],
              ["Segment tag", "CSV upload", "Analytics grouping only", "Plaintext"],
              ["Consent flag", "CSV upload (column: consent)", "Gate import — row skipped if false", "Boolean"],
              ["DND flag", "CSV upload (column: dnd)", "Block calling if true", "Boolean; also checked against DND registry"],
              ["Call outcome / intent", "Captured during call", "Dashboard analytics, retry logic", "Plaintext outcome label only"],
              ["Call recording", "Telephony provider", "Quality review by admin only", "Encrypted at rest; 30-day retention"],
              ["Speech transcript", "AI service (STT)", "Intent detection only — discarded after classification", "Not stored"],
              ["Organiser email", "Login form", "Authentication", "Hashed password (argon2); email plaintext"],
              ["Audit log entry", "System", "Compliance — who launched/paused/erased", "IP address, action, object ID; 90-day retention"],
            ].map(([data, source, purpose, storage]) => (
              <tr key={data}>
                <td style={tdStyle}><strong>{data}</strong></td>
                <td style={tdStyle}>{source}</td>
                <td style={tdStyle}>{purpose}</td>
                <td style={tdStyle}>{storage}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>

      {/* ── Processing location ──────────────────────────────────────────── */}
      <Section title="3. Processing Location">
        <table style={tableStyle}>
          <thead>
            <tr>
              {["System", "Location", "Notes"].map((h) => (
                <th key={h} style={thStyle}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[
              ["PostgreSQL database", "VPS — India (Mumbai region)", "Phone numbers and names AES-256-GCM encrypted at rest"],
              ["Redis cache", "Same VPS", "No personal data cached; only campaign state counters"],
              ["AI service (STT / TTS / intent)", "Same VPS (on-premise GPU)", "Audio processed in RAM only; no data written to disk by the AI service"],
              ["Call recordings", "Same VPS", "Encrypted before write; decrypted only for authorised admin playback"],
              ["Telephony (Exotel)", "Exotel cloud — India", "Only the E.164 number and caller ID are sent; no names or transcripts"],
              ["TTS edge voices (fallback)", "Microsoft Azure — global CDN", "Text sent is the rendered script segment, which contains no personal data"],
            ].map(([system, location, notes]) => (
              <tr key={system}>
                <td style={tdStyle}><strong>{system}</strong></td>
                <td style={tdStyle}>{location}</td>
                <td style={tdStyle}>{notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p style={{ marginTop: 14, fontSize: 13, color: "#5B6B7D" }}>
          No personal data is transferred outside India except to Exotel
          (Indian entity) and, for TTS fallback only, to Microsoft Azure. The
          script text sent for TTS contains no contact names or phone numbers.
        </p>
      </Section>

      {/* ── Retention ────────────────────────────────────────────────────── */}
      <Section title="4. Retention Periods">
        <table style={tableStyle}>
          <thead>
            <tr>
              {["Data", "Retention"].map((h) => (
                <th key={h} style={thStyle}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[
              ["Call recordings", "30 days (configurable via RECORDING_RETENTION_DAYS)"],
              ["Call events and raw webhook payloads", "90 days (configurable via EVENT_RETENTION_DAYS)"],
              ["Contact records", "Until the organiser deletes them or exercises right-to-erasure"],
              ["Audit log", "90 days, then purged automatically"],
              ["Campaign analytics aggregates", "Indefinite (anonymised — contact link nulled on erasure)"],
            ].map(([data, ret]) => (
              <tr key={data}>
                <td style={tdStyle}><strong>{data}</strong></td>
                <td style={tdStyle}>{ret}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>

      {/* ── Consent and opt-out ──────────────────────────────────────────── */}
      <Section title="5. Consent and Opt-Out">
        <p>
          Every contact must have <code>consent=true</code> in the uploaded CSV.
          Rows without consent are rejected at import. During a call, pressing
          or saying &quot;stop calling&quot; sets the contact&apos;s
          <code> opted_out</code> flag immediately; no further calls are placed
          to that number for this campaign. The DND list is checked at import
          time; matching numbers are skipped and not stored.
        </p>
      </Section>

      {/* ── Rights ───────────────────────────────────────────────────────── */}
      <Section title="6. Individual Rights">
        <p>
          Contacts whose data was imported may request erasure. An organiser
          or admin can trigger the right-to-erasure flow via
          <code> DELETE /api/contacts/&#123;id&#125;</code>, which deletes the
          contact record, deletes any associated recordings from disk, and
          nulls the contact link in campaign analytics (so aggregate statistics
          are preserved without identifying the individual).
        </p>
      </Section>

      {/* ── Security ─────────────────────────────────────────────────────── */}
      <Section title="7. Security Measures">
        <ul style={{ paddingLeft: 20, lineHeight: 1.9 }}>
          <li>Phone numbers and names encrypted with AES-256-GCM; key not stored in the database.</li>
          <li>HMAC-SHA256 phone hash used for de-duplication and lookup — no plaintext index.</li>
          <li>Call recordings encrypted before writing to disk.</li>
          <li>All API calls require a signed JWT (HS256, 12-hour expiry).</li>
          <li>HTTPS enforced via Caddy with automatic certificate renewal.</li>
          <li>SSH key-only access to the server; root login disabled.</li>
          <li>Unattended security upgrades enabled; <code>fail2ban</code> running.</li>
          <li>Every sensitive action (recording playback, contact erasure, campaign launch) is written to the audit log.</li>
        </ul>
      </Section>

      {/* ── Contact ──────────────────────────────────────────────────────── */}
      <Section title="8. Contact">
        <p>
          For data protection queries, contact the organising institution that
          ran the campaign. For platform-level queries, reach the Veylo team at
          the email address used during onboarding.
        </p>
      </Section>

      <div className="pgf" style={{ marginTop: 60 }}>
        <span>VEYLO / PRIVACY</span>
        <i>✳</i>
      </div>
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section style={{ marginBottom: 40 }}>
      <h2
        style={{
          font: "800 20px 'Manrope'",
          letterSpacing: "-.025em",
          marginBottom: 14,
          paddingBottom: 8,
          borderBottom: "1.5px solid rgba(0,0,0,.07)",
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <span
          style={{
            width: 18,
            height: 2,
            background: "var(--red)",
            display: "inline-block",
            flexShrink: 0,
          }}
        />
        {title}
      </h2>
      {children}
    </section>
  );
}

const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: 13,
  lineHeight: 1.5,
};
const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "8px 10px",
  background: "rgba(0,0,0,.04)",
  font: "700 12px 'Manrope'",
  borderBottom: "2px solid rgba(0,0,0,.08)",
};
const tdStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderBottom: "1px solid rgba(0,0,0,.06)",
  verticalAlign: "top",
};
