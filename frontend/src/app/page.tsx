import Link from "next/link";
import Image from "next/image";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Veylo — AI Calling Campaign Platform",
};

export default function LandingPage() {
  return (
    <>
      {/* Decorative blobs */}
      <div className="blob blob-1" aria-hidden="true" />
      <div className="blob blob-2" aria-hidden="true" />

      {/* Mobile top bar */}
      <header
        style={{
          display: "none",
          position: "fixed",
          inset: "0 0 auto 0",
          zIndex: 20,
          justifyContent: "space-between",
          alignItems: "center",
          padding: "10px 16px",
          background: "rgba(255,253,248,.94)",
          borderBottom: "1px solid rgba(23,38,58,.1)",
        }}
        className="mobile-top"
      >
        <span style={{ font: "800 20px 'Manrope'", letterSpacing: "-.03em" }}>
          Vey<b style={{ color: "var(--red)" }}>lo</b>
        </span>
        <Link href="/overview" className="vbtn vbtn-red vbtn-sm" style={{ textDecoration: "none" }}>
          NEW
        </Link>
      </header>

      {/* Fixed left rail (desktop) */}
      <aside
        style={{
          position: "fixed",
          inset: "0 auto 0 0",
          width: 200,
          padding: "26px 16px",
          background: "rgba(183,216,245,.34)",
          backdropFilter: "blur(10px)",
          WebkitBackdropFilter: "blur(10px)",
          borderRight: "1px solid rgba(23,38,58,.1)",
          display: "flex",
          flexDirection: "column",
          zIndex: 20,
        }}
        aria-label="Primary navigation"
      >
        <Link
          href="/"
          style={{
            font: "800 20px 'Manrope'",
            letterSpacing: "-.03em",
            margin: "0 8px 26px",
            textDecoration: "none",
            color: "var(--ink)",
          }}
        >
          Vey<b style={{ color: "var(--red)" }}>lo</b>
        </Link>
        {[
          { href: "/overview",  label: "Overview" },
          { href: "/campaigns", label: "Campaigns" },
          { href: "/contacts",  label: "Contacts" },
          { href: "/analytics", label: "Analytics" },
        ].map((item) => (
          <Link
            key={item.href}
            href={item.href}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "10px 12px",
              borderRadius: 12,
              textDecoration: "none",
              font: "600 14px 'Manrope'",
              color: "#4A5B6E",
              marginBottom: 4,
              transition: ".2s",
            }}
          >
            {item.label}
          </Link>
        ))}
      </aside>

      {/* Main hero content */}
      <main
        style={{
          marginLeft: 200,
          padding: "var(--gap)",
          position: "relative",
          zIndex: 1,
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            width: "min(1320px, 100%)",
            display: "grid",
            gap: "var(--gap)",
            gridTemplateColumns: "minmax(0,.9fr) minmax(0,1.2fr)",
            gridTemplateRows: "560px 300px",
          }}
        >
          {/* ── Copy panel ───────────────────────────────────────────── */}
          <section
            className="panel-in"
            style={{
              position: "relative",
              overflow: "hidden",
              border: "1px solid rgba(23,38,58,.1)",
              background: "var(--white)",
              padding: "50px 26px 22px",
              display: "flex",
              flexDirection: "column",
              animationDelay: ".05s",
            }}
          >
            <p className="eye">REACH, TRANSLATED</p>
            <h1
              style={{
                font: "800 clamp(46px,5.4vw,78px)/.94 'Manrope'",
                letterSpacing: "-.065em",
                margin: "0 0 28px",
                position: "relative",
                zIndex: 0,
              }}
            >
              <span style={{ display: "block", whiteSpace: "nowrap" }}>Every call.</span>
              <span style={{ display: "block", whiteSpace: "nowrap", color: "var(--red)" }}>Every language.</span>
              <span style={{ display: "block", whiteSpace: "nowrap" }}>
                <span className="hl">Greater reach.</span>
              </span>
            </h1>
            <p style={{ margin: "0 0 28px", maxWidth: "42ch", color: "#4A5B6E", fontSize: 15.5 }}>
              Event invitations that meet your guests where they are — with one considered call,
              in every language that matters.
            </p>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <Link href="/overview" className="vbtn vbtn-red" style={{ textDecoration: "none" }}>
                BUILD YOUR REACH <span>↗</span>
              </Link>
              <Link href="/overview" className="vbtn" style={{ textDecoration: "none" }}>
                OPEN WORKSPACE <span>→</span>
              </Link>
            </div>
            <p style={{ marginTop: 18, fontSize: 12, color: "#5B6B7D" }}>
              Your next event brief is ready to reach the room.
            </p>
            <div
              style={{
                marginTop: "auto",
                borderTop: "1px solid rgba(23,38,58,.15)",
                paddingTop: 14,
                display: "flex",
                justifyContent: "space-between",
                font: "500 10.5px 'Manrope'",
                letterSpacing: ".1em",
                color: "#5B6B7D",
              }}
            >
              <span>DESIGNED FOR THE WHOLE ROOM</span>
              <i style={{ color: "var(--red)", fontStyle: "normal" }}>✳</i>
            </div>
          </section>

          {/* ── Hero visual panel ─────────────────────────────────────── */}
          <section
            className="panel-in"
            style={{
              position: "relative",
              overflow: "hidden",
              border: "1px solid rgba(23,38,58,.1)",
              background: "var(--blue)",
              perspective: 1100,
              animationDelay: ".15s",
            }}
          >
            {/* Floating sun */}
            <span className="sun" aria-hidden="true" />

            {/* Network SVG */}
            <svg
              viewBox="0 0 764 560"
              preserveAspectRatio="xMidYMid slice"
              aria-hidden="true"
              style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
            >
              <path id="lp1" className="net-path" d="M382 250 C 450 120, 600 90, 690 130"/>
              <path id="lp2" className="net-path" d="M382 250 C 500 250, 620 290, 720 320"/>
              <path id="lp3" className="net-path" d="M382 250 C 450 380, 560 430, 650 450"/>
              <path id="lp4" className="net-path" d="M382 250 C 300 360, 180 440, 110 470"/>
              <circle className="net-node" cx="690" cy="130" r="6"/>
              <circle className="net-node" cx="720" cy="320" r="6"/>
              <circle className="net-node" cx="650" cy="450" r="6"/>
              <circle className="net-node" cx="110" cy="470" r="6"/>
              <text className="net-label" x="625" y="115">Malayalam</text>
              <text className="net-label" x="660" y="306">English</text>
              <text className="net-label" x="605" y="474">Hindi</text>
              <text className="net-label" x="70"  y="496">Tamil</text>
              <circle className="net-pulse" r="4">
                <animateMotion dur="4.5s" repeatCount="indefinite"><mpath href="#lp1"/></animateMotion>
              </circle>
              <circle className="net-pulse" r="4">
                <animateMotion dur="5.5s" begin="1s" repeatCount="indefinite"><mpath href="#lp2"/></animateMotion>
              </circle>
              <circle className="net-pulse" r="4">
                <animateMotion dur="5s" begin="2s" repeatCount="indefinite"><mpath href="#lp3"/></animateMotion>
              </circle>
              <circle className="net-pulse" r="4">
                <animateMotion dur="6s" begin=".5s" repeatCount="indefinite"><mpath href="#lp4"/></animateMotion>
              </circle>
            </svg>

            {/* Phone mockup */}
            <div
              style={{
                position: "absolute",
                left: "50%",
                top: 70,
                width: 204,
                height: 398,
                marginLeft: -102,
                borderRadius: 34,
                background: "var(--ink)",
                padding: 7,
                boxShadow: "0 36px 50px -22px rgba(23,38,58,.6)",
                zIndex: 3,
              }}
            >
              <div
                style={{
                  height: "100%",
                  borderRadius: 28,
                  background: "var(--white)",
                  padding: "14px 14px 12px",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  textAlign: "center",
                  position: "relative",
                }}
              >
                <div style={{ width: 70, height: 16, borderRadius: 9, background: "var(--ink)", marginBottom: 12 }} />
                <div style={{ display: "flex", justifyContent: "space-between", width: "100%", font: "600 9px 'Manrope'" }}>
                  <span>● veylo</span>
                  <em style={{ background: "var(--yellow)", fontStyle: "normal", padding: "1px 5px", fontSize: 8 }}>LIVE</em>
                </div>
                <div style={{ width: 56, height: 56, borderRadius: "50%", background: "rgba(225,6,0,.1)", border: "1.5px dashed var(--red)", display: "grid", placeItems: "center", font: "800 14px 'Manrope'", color: "var(--red)", margin: "14px 0 8px" }}>VY</div>
                <small style={{ font: "500 8px 'Manrope'", letterSpacing: ".1em", color: "#5B6B7D" }}>INCOMING EVENT CALL</small>
                <h4 style={{ font: "800 20px 'Manrope'", letterSpacing: "-.04em", margin: "3px 0" }}>National Tech Summit</h4>
                <p style={{ fontSize: 9, color: "#5B6B7D", margin: 0 }}>12 Nov · Kochi</p>
                <div className="phone-wave" style={{ margin: "10px 0 auto" }}>
                  {Array.from({ length: 9 }).map((_, i) => <i key={i} />)}
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", width: "100%", padding: "0 10px" }}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", font: "500 8px 'Manrope'", color: "#5B6B7D", gap: 3 }}>
                    <b style={{ width: 38, height: 38, borderRadius: "50%", display: "grid", placeItems: "center", color: "#fff", fontSize: 18, background: "var(--ink)" }}>+</b>
                    Decline
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", font: "500 8px 'Manrope'", color: "#5B6B7D", gap: 3 }}>
                    <b style={{ width: 38, height: 38, borderRadius: "50%", display: "grid", placeItems: "center", color: "#fff", fontSize: 18, background: "var(--red)" }}>↑</b>
                    Accept
                  </div>
                </div>
              </div>
            </div>

            {/* Chip badges */}
            <div style={{ position: "absolute", zIndex: 4, display: "flex", alignItems: "center", gap: 10, font: "600 12px 'Manrope'", left: "6%", top: "9%" }}>
              <i style={{ width: 26, height: 26, borderRadius: "50%", display: "grid", placeItems: "center", font: "800 9px 'Manrope'", fontStyle: "normal", background: "var(--yellow)" }}>01</i>
              <div>One call<small style={{ display: "block", font: "400 10px 'DM Sans'", color: "#33465C" }}>four languages</small></div>
            </div>
            <div style={{ position: "absolute", zIndex: 4, display: "flex", alignItems: "center", gap: 10, font: "600 12px 'Manrope'", right: "6%", bottom: "28%" }}>
              <i style={{ width: 28, height: 28, borderRadius: "50%", display: "grid", placeItems: "center", font: "800 9px 'Manrope'", fontStyle: "normal", background: "var(--red)", color: "#fff" }}>✳</i>
              <div>96.8%<small style={{ display: "block", font: "400 10px 'DM Sans'", color: "#33465C" }}>sample metric</small></div>
            </div>

            {/* Cap */}
            <div style={{ position: "absolute", left: "var(--pad)", right: "var(--pad)", bottom: 16, display: "flex", justifyContent: "space-between", font: "500 10px 'Manrope'", letterSpacing: ".1em", color: "#33465C", zIndex: 4 }}>
              <span>VEYLO / MOBILE INVITATION</span>
              <span>SCROLL TO EXPLORE ↓</span>
            </div>
          </section>

          {/* ── Bottom left: audience illustration ───────────────────── */}
          <section
            className="panel-in"
            style={{
              gridColumn: 1,
              display: "grid",
              gridTemplateColumns: ".9fr 1.1fr",
              padding: 0,
              border: 0,
              animationDelay: ".25s",
            }}
          >
            {/* Photo/illustration side — Veylo boy character */}
            <div
              style={{
                position: "relative",
                background: "var(--blue)",
                overflow: "hidden",
                display: "flex",
                alignItems: "flex-end",
                justifyContent: "center",
              }}
              role="img"
              aria-label="Veylo presenter character"
            >
              {/* Decorative yellow circle — top-right accent */}
              <span aria-hidden="true" style={{
                position: "absolute", top: 18, right: 18,
                width: 38, height: 38, borderRadius: "50%",
                background: "var(--yellow)", opacity: .7,
                pointerEvents: "none",
              }} />
              {/* Decorative yellow circle — bottom-left accent */}
              <span aria-hidden="true" style={{
                position: "absolute", bottom: 22, left: 14,
                width: 22, height: 22, borderRadius: "50%",
                background: "var(--yellow)", opacity: .5,
                pointerEvents: "none",
              }} />
              <Image
                src="/veylo-boy.png"
                alt="Veylo presenter"
                width={200}
                height={260}
                style={{
                  objectFit: "contain",
                  objectPosition: "bottom center",
                  position: "relative",
                  zIndex: 1,
                  height: "82%",
                  width: "auto",
                  maxWidth: "90%",
                }}
                priority
              />
            </div>
            {/* Room text */}
            <div style={{ background: "var(--blue)", padding: "22px 24px", display: "flex", flexDirection: "column" }}>
              <p style={{ font: "600 10px 'Manrope'", letterSpacing: ".12em", color: "#33465C", margin: "0 0 6px" }}>03 / 04</p>
              <p className="eye" style={{ marginBottom: 10, fontSize: 10 }}>THE ROOM, OPENED</p>
              <h2 style={{ font: "800 33px/.98 'Manrope'", letterSpacing: "-.06em", margin: "0 0 auto" }}>More people in the moment.</h2>
              <p style={{ margin: "10px 0 0", fontSize: 13, color: "#33465C" }}>Turn an invitation into a welcome — before anyone has to ask what happens next.</p>
            </div>
          </section>

          {/* ── Bottom right: features ────────────────────────────────── */}
          <section
            className="panel-in"
            style={{
              position: "relative",
              overflow: "hidden",
              border: 0,
              background: "var(--yellow)",
              padding: "26px 28px",
              display: "flex",
              flexDirection: "column",
              animationDelay: ".35s",
            }}
          >
            <p style={{ margin: "0 0 4px", font: "600 10px 'Manrope'", letterSpacing: ".12em" }}>04 / 04</p>
            <p className="eye" style={{ marginBottom: 12, color: "var(--ink)" }}>IN THE ROOM</p>
            <h2 style={{ font: "800 clamp(34px,3.6vw,48px)/1 'Manrope'", letterSpacing: "-.065em", margin: "0 0 auto" }}>Reach is a feeling.</h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 22, borderTop: "1px solid rgba(23,38,58,.35)", paddingTop: 14 }}>
              {[
                { icon: "M12 12m-6 0a6 6 0 1 0 12 0a6 6 0 1 0 -12 0", label: "Human, at scale",      desc: "A thoughtful call, never a blast." },
                { icon: "M3 12c3-6 6 6 9 0s6 6 9 0",                   label: "Made multilingual",   desc: "One message, every voice." },
                { icon: "M4 6h16v12H4z",                               label: "Measured in real time",desc: "See the room come together." },
              ].map((f) => (
                <div key={f.label} style={{ display: "grid", gridTemplateColumns: "26px 1fr", gap: 10 }}>
                  <svg viewBox="0 0 24 24" style={{ width: 26, height: 26, padding: 5, background: "var(--ink)", stroke: "var(--yellow)", fill: "none", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" }}>
                    <path d={f.icon}/>
                  </svg>
                  <div>
                    <b style={{ display: "block", font: "700 13px 'Manrope'" }}>{f.label}</b>
                    <span style={{ fontSize: 12, lineHeight: 1.4, color: "#4A4000", display: "block" }}>{f.desc}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </main>
    </>
  );
}
