import Link from "next/link";
import Image from "next/image";
import type { Metadata } from "next";
import Sidebar from "@/components/layout/Sidebar";
import SplitText from "@/components/motion/SplitText";
import HeroDepth from "@/components/landing/HeroDepth";
import IsometricTileSection from "@/components/landing/IsometricTileSection";
import Reveal from "@/components/motion/Reveal";
import Tilt from "@/components/motion/Tilt";

export const metadata: Metadata = {
  title: "Veylo — AI Calling Campaign Platform",
};

export default function LandingPage() {
  return (
    <>
      {/* Decorative background blobs */}
      <div className="blob blob-1" aria-hidden="true" />
      <div className="blob blob-2" aria-hidden="true" />

      {/* Mobile top header bar */}
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

      {/* Navigation Rail Sidebar */}
      <Sidebar />

      {/* Main Hero & Content Grid */}
      <main
        style={{
          marginLeft: 224,
          padding: "var(--gap)",
          position: "relative",
          zIndex: 1,
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
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
            gridTemplateRows: "auto auto",
          }}
        >
          {/* ── 1. Hero Copy Panel with 3D SplitText Headline ────────────── */}
          <Reveal direction="left" staggerIndex={0}>
            <Tilt maxDegreeX={6} maxDegreeY={10}>
              <section
                style={{
                  position: "relative",
                  overflow: "hidden",
                  border: "1px solid rgba(23,38,58,.1)",
                  background: "var(--white)",
                  padding: "44px 26px 26px",
                  display: "flex",
                  flexDirection: "column",
                  minHeight: 520,
                  borderRadius: 16,
                }}
              >
                <p className="eye">REACH, TRANSLATED</p>

                {/* 3D Letter SplitText Headline */}
                <SplitText
                  text="Every call. Every language. Greater reach."
                  as="h1"
                  className="font-extrabold text-slate-900 mb-6 leading-tight tracking-tight text-3xl sm:text-4xl lg:text-5xl"
                />

                <p style={{ margin: "0 0 28px", maxWidth: "42ch", color: "#4A5B6E", fontSize: 15.5 }}>
                  Event invitations that meet your guests where they are — with one considered call,
                  in every language that matters.
                </p>

                <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
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
            </Tilt>
          </Reveal>

          {/* ── 2. Hero 3D Interactive Depth Stage ─────────────────────── */}
          <Reveal direction="right" staggerIndex={1}>
            <section
              style={{
                position: "relative",
                overflow: "hidden",
                border: "1px solid rgba(23,38,58,.1)",
                background: "var(--blue)",
                borderRadius: 16,
                height: 520,
              }}
            >
              <HeroDepth />
            </section>
          </Reveal>

          {/* ── 3. Bottom Left: Audience Illustration Panel ───────────── */}
          <Reveal direction="left" staggerIndex={2} className="col-span-1">
            <section
              style={{
                display: "grid",
                gridTemplateColumns: ".9fr 1.1fr",
                padding: 0,
                border: "1px solid rgba(23,38,58,.1)",
                borderRadius: 16,
                overflow: "hidden",
                minHeight: 280,
              }}
            >
              {/* Veylo Boy Character */}
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
                <span
                  aria-hidden="true"
                  style={{
                    position: "absolute",
                    top: 18,
                    right: 18,
                    width: 38,
                    height: 38,
                    borderRadius: "50%",
                    background: "var(--yellow)",
                    opacity: 0.7,
                    pointerEvents: "none",
                  }}
                />
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

              {/* Room Text */}
              <div style={{ background: "var(--blue)", padding: "22px 24px", display: "flex", flexDirection: "column" }}>
                <p style={{ font: "600 10px 'Manrope'", letterSpacing: ".12em", color: "#33465C", margin: "0 0 6px" }}>03 / 04</p>
                <p className="eye" style={{ marginBottom: 10, fontSize: 10 }}>THE ROOM, OPENED</p>
                <h2 style={{ font: "800 30px/.98 'Manrope'", letterSpacing: "-.06em", margin: "0 0 auto" }}>More people in the moment.</h2>
                <p style={{ margin: "10px 0 0", fontSize: 13, color: "#33465C" }}>Turn an invitation into a welcome — before anyone has to ask what happens next.</p>
              </div>
            </section>
          </Reveal>

          {/* ── 4. Bottom Right: Features Panel with Popout Icons ─────── */}
          <Reveal direction="right" staggerIndex={3} className="col-span-1">
            <section
              style={{
                position: "relative",
                overflow: "hidden",
                border: "1px solid rgba(23,38,58,.1)",
                borderRadius: 16,
                background: "var(--yellow)",
                padding: "26px 28px",
                display: "flex",
                flexDirection: "column",
                minHeight: 280,
              }}
            >
              <p style={{ margin: "0 0 4px", font: "600 10px 'Manrope'", letterSpacing: ".12em" }}>04 / 04</p>
              <p className="eye" style={{ marginBottom: 12, color: "var(--ink)" }}>IN THE ROOM</p>
              <h2 style={{ font: "800 clamp(32px,3.6vw,44px)/1 'Manrope'", letterSpacing: "-.065em", margin: "0 0 auto" }}>Reach is a feeling.</h2>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16, borderTop: "1px solid rgba(23,38,58,.35)", paddingTop: 14 }}>
                {[
                  { icon: "M12 12m-6 0a6 6 0 1 0 12 0a6 6 0 1 0 -12 0", label: "Human, at scale", desc: "A thoughtful call, never a blast." },
                  { icon: "M3 12c3-6 6 6 9 0s6 6 9 0", label: "Made multilingual", desc: "One message, every voice." },
                  { icon: "M4 6h16v12H4z", label: "Measured in real time", desc: "See the room come together." },
                ].map((f, i) => (
                  <div key={f.label} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <svg
                      viewBox="0 0 24 24"
                      strokeWidth={2}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      style={{
                        width: 32,
                        height: 32,
                        padding: 6,
                        background: "var(--ink)",
                        stroke: "var(--yellow)",
                        fill: "none",
                        borderRadius: 8,
                        boxShadow: "3px 3px 0 #E10600",
                      }}
                    >
                      <path d={f.icon} />
                    </svg>
                    <div>
                      <b style={{ display: "block", font: "700 12.5px 'Manrope'", color: "var(--ink)" }}>{f.label}</b>
                      <span style={{ fontSize: 11.5, lineHeight: 1.35, color: "#4A4000", display: "block", marginTop: 2 }}>{f.desc}</span>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </Reveal>
        </div>

        {/* ── 5. Isometric 3D Language Stage Section ───────────────────── */}
        <div style={{ width: "min(1320px, 100%)", marginTop: "var(--gap)" }}>
          <IsometricTileSection />
        </div>
      </main>
    </>
  );
}
