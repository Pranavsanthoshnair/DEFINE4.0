import type { Metadata } from "next";
import PageHeader from "@/components/ui/PageHeader";

export const metadata: Metadata = { title: "Templates — Veylo" };

const KINDS = ["invitation", "reminder", "update"];
const LANGS = ["English", "Malayalam", "Hindi", "Tamil"];

const SAMPLE: Record<string, string> = {
  English:
    "Hello {name}, you're invited to {event_name} on {event_date} in {city}. Press 1 to confirm, 2 to decline, or 3 to request a callback.",
  Malayalam:
    "നമസ്കാരം {name}, {event_date}-ന് {city}-ൽ നടക്കുന്ന {event_name}-ലേക്ക് ക്ഷണിക്കുന്നു.",
  Hindi:
    "नमस्ते {name}, आपको {event_date} को {city} में {event_name} के लिए आमंत्रित किया जाता है।",
  Tamil:
    "வணக்கம் {name}, {event_date} அன்று {city} இல் நடைபெறும் {event_name} நிகழ்வுக்கு உங்களை அழைக்கிறோம்.",
};

export default function TemplatesPage() {
  return (
    <div className="page-in" style={{ maxWidth: 1180, margin: "0 auto", padding: "30px 28px 60px" }}>
      <PageHeader
        eyebrow="templates"
        title="Templates"
        subtitle="Reusable wording for every language. Use {name}, {event_name}, {event_date} and {city}."
        tagline="Words that travel."
        bubble="Say it in any language"
        mascot="girl"
      />

      {/* Kind tabs */}
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
        {KINDS.map((k, i) => (
          <button
            key={k}
            className="vbtn vbtn-sm"
            style={{
              background: i === 0 ? "var(--yellow)" : "var(--white)",
              color: "var(--ink)",
              border: "1.5px solid var(--ink)",
            }}
          >
            {k}
          </button>
        ))}
      </div>

      {/* Language tabs */}
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
        {LANGS.map((l, i) => (
          <button
            key={l}
            className="vbtn vbtn-sm"
            style={{
              background: i === 0 ? "var(--ink)" : "var(--white)",
              color: i === 0 ? "var(--white)" : "var(--ink)",
              border: "1.5px solid var(--ink)",
            }}
          >
            {l}
          </button>
        ))}
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0,1.5fr) minmax(0,1fr)",
          gap: "var(--gap)",
        }}
      >
        {/* Editor */}
        <div className="glass" style={{ padding: "18px 20px" }}>
          <h3
            style={{
              font: "800 17px 'Manrope'",
              letterSpacing: "-.03em",
              margin: "0 0 12px",
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}
          >
            <span
              style={{ width: 18, height: 1.5, background: "var(--red)", display: "inline-block" }}
            />
            Edit message
          </h3>
          <textarea
            className="vfield"
            aria-label="Template text"
            defaultValue={SAMPLE.English}
            style={{ marginBottom: 10 }}
          />
          <button className="vbtn vbtn-sm vbtn-ink">SAVE TEMPLATE</button>
        </div>

        {/* Phone preview */}
        <div>
          <div className="phone-wrap">
            <div className="phone-shell">
              <div className="phone-screen">
                <div className="phone-notch" />
                <div className="phone-avatar">VY</div>
                <small
                  style={{
                    font: "600 8px 'Manrope'",
                    letterSpacing: ".1em",
                    color: "#5B6B7D",
                  }}
                >
                  INCOMING EVENT CALL
                </small>
                <b
                  style={{
                    font: "800 17px 'Manrope'",
                    letterSpacing: "-.04em",
                  }}
                >
                  National Tech Summit
                </b>
                <p style={{ fontSize: 12, lineHeight: 1.45, margin: "6px 0", color: "#33465C" }}>
                  {SAMPLE.English.replace("{name}", "Anjali")
                    .replace("{event_name}", "National Tech Summit")
                    .replace("{event_date}", "12 Nov")
                    .replace("{city}", "Kochi")}
                </p>
                <div className="phone-wave">
                  {Array.from({ length: 9 }).map((_, i) => (
                    <i key={i} />
                  ))}
                </div>
                <div className="phone-actions">
                  <span style={{ background: "var(--ink)" }}>2</span>
                  <span style={{ background: "var(--red)" }}>1</span>
                </div>
              </div>
            </div>
          </div>
          <p style={{ textAlign: "center", marginTop: 8 }}>
            <small style={{ color: "#5B6B7D", fontSize: 11 }}>Preview with sample values</small>
          </p>
        </div>
      </div>

      <div className="pgf">
        <span>VEYLO / TEMPLATES</span>
        <i>✳</i>
      </div>
    </div>
  );
}
