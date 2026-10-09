import Image from "next/image";

interface PageHeaderProps {
  eyebrow?: string;
  title: React.ReactNode;
  subtitle?: string;
  tagline?: string;
  bubble?: string;
  mascot?: "boy" | "girl";
  action?: React.ReactNode;
}

export default function PageHeader({
  eyebrow,
  title,
  subtitle,
  tagline,
  bubble,
  mascot,
  action,
}: PageHeaderProps) {
  return (
    <div
      className="relative overflow-hidden rounded-2xl mb-5 flex items-center justify-between"
      style={{
        background: "rgba(183,216,245,.38)",
        border: "1px solid rgba(183,216,245,.6)",
        padding: "24px 28px",
        minHeight: 120,
        gap: 16,
      }}
    >
      {/* Subtle decorative lines — desktop only */}
      <svg
        viewBox="0 0 420 160"
        preserveAspectRatio="xMaxYMid slice"
        aria-hidden="true"
        className="hidden md:block"
        style={{
          position: "absolute", right: mascot ? 180 : 0,
          top: 0, height: "100%", width: "30%",
          pointerEvents: "none", zIndex: 1, opacity: 0.5,
        }}
      >
        <path stroke="#17263A" strokeWidth="1" fill="none" strokeDasharray="4 4" d="M120 80 C190 20 300 20 390 50" />
        <path stroke="#17263A" strokeWidth="1" fill="none" strokeDasharray="4 4" d="M120 80 C220 100 320 110 400 120" />
        <circle fill="#EA1D2C" cx="120" cy="80" r="5" opacity="0.7" />
        <circle fill="#17263A" cx="390" cy="50" r="4" opacity="0.4" />
        <circle fill="#17263A" cx="400" cy="120" r="4" opacity="0.4" />
      </svg>

      {/* Main text */}
      <div className="relative z-10 flex-1 min-w-0">
        {eyebrow && (
          <p className="flex items-center gap-2 mb-1" style={{ font: "600 11px/1 'Manrope', sans-serif", letterSpacing: ".1em", textTransform: "uppercase", color: "#5A6E84" }}>
            <span style={{ width: 18, height: 1.5, background: "#EA1D2C", display: "inline-block", flex: "none" }} />
            {eyebrow}
          </p>
        )}
        <h1 style={{ font: "800 clamp(22px,3.5vw,38px)/1.1 'Manrope', sans-serif", letterSpacing: "-.04em", margin: "0 0 6px", color: "#17263A" }}>
          {title}
        </h1>
        {subtitle && <p style={{ margin: "0 0 8px", color: "#33465C", fontSize: 14 }}>{subtitle}</p>}
        {tagline && <em style={{ fontFamily: "'Caveat', cursive", fontSize: 18, color: "#EA1D2C", fontStyle: "italic" }}>{tagline}</em>}
        {action && <div className="mt-4">{action}</div>}
      </div>

      {/* Mascot — hidden on small screens */}
      {mascot && (
        <div className="hidden sm:flex flex-col items-center relative z-10 flex-none" style={{ gap: 4 }}>
          {bubble && (
            <span
              style={{
                background: "#fff",
                border: "1.5px solid #17263A",
                borderRadius: "12px 12px 12px 4px",
                padding: "4px 10px",
                fontSize: 11,
                fontWeight: 700,
                fontFamily: "Manrope, sans-serif",
                whiteSpace: "nowrap",
                boxShadow: "2px 2px 0 #17263A",
              }}
            >
              {bubble}
            </span>
          )}
          <Image
            src={mascot === "boy" ? "/veylo-boy.png" : "/veylo-girl.png"}
            alt=""
            width={90}
            height={110}
            style={{ objectFit: "contain", objectPosition: "bottom", width: "auto", height: "110px" }}
            priority={true}
          />
        </div>
      )}
    </div>
  );
}
