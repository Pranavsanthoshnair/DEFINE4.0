import type { Metadata } from "next";
import Link from "next/link";
import Sidebar from "@/components/layout/Sidebar";

export const metadata: Metadata = {
  title: "Dashboard — Veylo",
};

const STAT_CARDS = [
  { label: "Active Campaigns", value: "—", icon: "📣" },
  { label: "Calls Today", value: "—", icon: "📞" },
  { label: "Answer Rate", value: "—", icon: "✅" },
  { label: "Pending Retries", value: "—", icon: "🔁" },
];

export default function DashboardPage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 p-6 space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Dashboard</h1>
            <p className="text-gray-400 text-sm mt-0.5">
              Campaign overview and live activity
            </p>
          </div>
          <Link
            href="/campaigns"
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-sm font-medium transition-colors"
          >
            + New Campaign
          </Link>
        </div>

        {/* Stat Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {STAT_CARDS.map((s) => (
            <div key={s.label} className="glass p-5 flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400 uppercase tracking-wider">
                  {s.label}
                </span>
                <span className="text-xl">{s.icon}</span>
              </div>
              <span className="text-3xl font-bold text-white">{s.value}</span>
              <span className="text-xs text-gray-600">
                Live data once campaigns are active
              </span>
            </div>
          ))}
        </div>

        {/* Recent Campaigns Placeholder */}
        <div className="glass p-6">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">
            Recent Campaigns
          </h2>
          <div className="flex flex-col items-center justify-center py-12 text-center gap-3">
            <span className="text-4xl">📣</span>
            <p className="text-gray-400 text-sm">No campaigns yet.</p>
            <Link
              href="/campaigns"
              className="text-indigo-400 hover:text-indigo-300 text-sm underline underline-offset-2 transition-colors"
            >
              Create your first campaign →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
