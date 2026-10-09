import type { Metadata } from "next";
import Sidebar from "@/components/layout/Sidebar";

export const metadata: Metadata = { title: "Analytics — Veylo" };

const PLACEHOLDER_METRICS = [
  { label: "Total Calls Made", value: "—" },
  { label: "Answer Rate", value: "—" },
  { label: "Avg Call Duration", value: "—" },
  { label: "Retry Success Rate", value: "—" },
];

export default function AnalyticsPage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 p-6 space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Analytics</h1>
          <p className="text-gray-400 text-sm mt-0.5">
            Campaign performance and recipient-level call history
          </p>
        </div>

        {/* Metric cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {PLACEHOLDER_METRICS.map((m) => (
            <div key={m.label} className="glass p-5 flex flex-col gap-1">
              <span className="text-xs text-gray-400 uppercase tracking-wider">
                {m.label}
              </span>
              <span className="text-2xl font-bold">{m.value}</span>
            </div>
          ))}
        </div>

        {/* Charts placeholder */}
        <div className="glass p-8 flex flex-col items-center justify-center text-center gap-3 min-h-[240px]">
          <span className="text-4xl">📈</span>
          <p className="text-gray-400 text-sm">
            Charts will appear here once campaigns are active.
          </p>
        </div>
      </div>
    </div>
  );
}
