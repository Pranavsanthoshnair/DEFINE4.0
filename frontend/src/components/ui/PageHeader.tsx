import Image from "next/image";

interface PageHeaderProps {
  eyebrow?: string;
  title: React.ReactNode;
  subtitle?: string;
  tagline?: string;
  bubble?: string;
  /** "boy" | "girl" — which mascot to show. Omit to hide mascot. */
  mascot?: "boy" | "girl";
  action?: React.ReactNode;
}

/**
 * The blue page header (.ph) from the reference design.
 * Includes the decorative network SVG, speech bubble, and mascot image.
 */
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
    <div className="ph" style={{ paddingRight: mascot ? 220 : 28 }}>
      {/* Decorative network SVG (top-right) */}
      <svg
        viewBox="0 0 420 160"
        preserveAspectRatio="xMaxYMid slice"
        aria-hidden="true"
        style={{
          position: "absolute", right: mascot ? 190 : 0,
          top: 0, height: "100%",
          width: "min(34%, 320px)",
          pointerEvents: "none", zIndex: 1,
        }}
      >
        <path className="net-path" d="M120 90 C190 20 300 20 390 50"/>
        <path className="net-path" d="M120 90 C220 100 320 110 400 120"/>
        <path className="net-path" d="M120 90 C180 150 260 160 330 150"/>
        <circle className="net-node" cx="120" cy="90" r="6"/>
        <circle className="net-node" cx="390" cy="50" r="5"/>
        <circle className="net-node" cx="400" cy="120" r="5"/>
        <circle className="net-node" cx="330" cy="150" r="5"/>
        <circle className="net-pulse" r="4">
          <animateMotion dur="4.5s" repeatCount="indefinite" path="M120 90 C190 20 300 20 390 50"/>
        </circle>
        <circle className="net-pulse" r="4">
          <animateMotion dur="5.5s" begin="1s" repeatCount="indefinite" path="M120 90 C220 100 320 110 400 120"/>
        </circle>
        <circle className="net-pulse" r="4">
          <animateMotion dur="5s" begin="2s" repeatCount="indefinite" path="M120 90 C180 150 260 160 330 150"/>
        </circle>
      </svg>

      {/* Floating yellow dot */}
      <span
        aria-hidden="true"
        style={{
          position: "absolute", right: "18%", top: 16,
          width: 30, height: 30, borderRadius: "50%",
          background: "var(--yellow)", zIndex: 1,
          animation: "float 6s ease-in-out infinite",
        }}
      />

      {/* Main text content */}
      <div className="ph-inner">
        {eyebrow && <p className="eye" style={{ textTransform: "uppercase" }}>{eyebrow}</p>}
        <h2 style={{
          font: "800 clamp(28px,4vw,44px)/1 'Manrope'",
          letterSpacing: "-.05em", margin: "0 0 6px",
          position: "relative", zIndex: 0,
        }}>
          {title}
        </h2>
        {subtitle && <p style={{ margin: 0, color: "#33465C" }}>{subtitle}</p>}
        {tagline && <em className="cal">{tagline}</em>}
      </div>

      {/* Action slot */}
      {action && (
        <div style={{ position: "relative", zIndex: 3 }}>
          {action}
        </div>
      )}

      {/* Mascot + speech bubble */}
      {mascot && (
        <div className="mascot-wrap" aria-hidden="true">
          {bubble && <span className="speech-bubble">{bubble}</span>}
          <Image
            src={mascot === "boy" ? "/veylo-boy.png" : "/veylo-girl.png"}
            alt=""
            width={100}
            height={130}
            className="mascot"
            style={{ objectFit: "contain" }}
            priority={false}
          />
        </div>
      )}
    </div>
  );
}
