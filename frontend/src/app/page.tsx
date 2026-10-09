import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="min-h-screen flex flex-col">
      {/* ── Nav ─────────────────────────────────────────────────────────── */}
      <nav className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <span className="text-xl font-bold tracking-tight gradient-text">
          Veylo
        </span>
        <div className="flex items-center gap-4">
          <Link
            href="/dashboard"
            className="text-sm text-gray-400 hover:text-white transition-colors"
          >
            Dashboard
          </Link>
          <Link
            href="/dashboard"
            className="text-sm px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 transition-colors font-medium"
          >
            Get Started →
          </Link>
        </div>
      </nav>

      {/* ── Hero ────────────────────────────────────────────────────────── */}
      <section className="flex-1 flex flex-col items-center justify-center text-center px-6 py-24 gap-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-indigo-300 text-xs font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
          DEFINE 4.0 · Hackathon Project
        </div>

        <h1 className="text-5xl md:text-6xl font-bold max-w-3xl leading-tight">
          AI-assisted{" "}
          <span className="gradient-text">multilingual</span> calling campaigns
        </h1>

        <p className="text-gray-400 text-lg max-w-xl">
          Turn a campaign brief into a validated calling workflow. Connect each
          call response to a clear next action with traceable evidence.
        </p>

        <div className="flex flex-col sm:flex-row items-center gap-4">
          <Link
            href="/campaigns"
            className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 transition-all font-semibold text-sm shadow-lg shadow-indigo-500/20"
          >
            Create Campaign
          </Link>
          <Link
            href="/dashboard"
            className="px-6 py-3 rounded-xl border border-gray-700 hover:border-gray-500 transition-colors text-sm text-gray-300"
          >
            View Dashboard
          </Link>
        </div>
      </section>

      {/* ── Feature Grid ────────────────────────────────────────────────── */}
      <section className="px-6 pb-24 max-w-5xl mx-auto w-full grid grid-cols-1 md:grid-cols-3 gap-4">
        {FEATURES.map((f) => (
          <div key={f.title} className="glass p-5 flex flex-col gap-2">
            <span className="text-2xl">{f.icon}</span>
            <h2 className="font-semibold text-sm text-white">{f.title}</h2>
            <p className="text-xs text-gray-400 leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </section>

      <footer className="border-t border-gray-800 px-6 py-4 text-center text-xs text-gray-600">
        Veylo · DEFINE 4.0 Hackathon
      </footer>
    </main>
  );
}

const FEATURES = [
  {
    icon: "🤖",
    title: "AI Script Generation",
    desc: "Turn a campaign brief into polished call scripts with language variants in seconds.",
  },
  {
    icon: "📞",
    title: "Exotel Outbound Calling",
    desc: "Launch campaigns at scale with automatic retry logic and live status tracking.",
  },
  {
    icon: "📊",
    title: "Real-time Analytics",
    desc: "Monitor campaign progress, response rates, and recipient-level call history.",
  },
  {
    icon: "🌍",
    title: "Multilingual Support",
    desc: "Generate and deliver call scripts in multiple languages for diverse audiences.",
  },
  {
    icon: "📋",
    title: "Contact Import",
    desc: "Upload contacts via CSV with built-in validation and deduplication.",
  },
  {
    icon: "🔁",
    title: "Smart Retry Rules",
    desc: "Configure retry logic per campaign to maximise contact reach.",
  },
];
