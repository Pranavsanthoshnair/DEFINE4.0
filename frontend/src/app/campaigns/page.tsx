import type { Metadata } from "next";
import Link from "next/link";
import Sidebar from "@/components/layout/Sidebar";

export const metadata: Metadata = { title: "Campaigns — Veylo" };

export default function CampaignsPage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Campaigns</h1>
            <p className="text-gray-400 text-sm mt-0.5">
              Manage and launch your calling campaigns
            </p>
          </div>
          <button
            disabled
            title="Campaign creation wizard — coming soon"
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            + New Campaign
          </button>
        </div>

        {/* Filter bar stub */}
        <div className="flex gap-2">
          {["All", "Draft", "Active", "Paused", "Completed"].map((s) => (
            <button
              key={s}
              className="px-3 py-1.5 rounded-lg text-xs font-medium border border-gray-700 text-gray-400 hover:border-indigo-500 hover:text-white transition-colors first:bg-indigo-600 first:border-indigo-600 first:text-white"
            >
              {s}
            </button>
          ))}
        </div>

        {/* Empty state */}
        <div className="glass p-12 flex flex-col items-center text-center gap-4">
          <span className="text-5xl">🚀</span>
          <h2 className="text-lg font-semibold">No campaigns yet</h2>
          <p className="text-gray-400 text-sm max-w-sm">
            Create your first campaign and Veylo will guide you through script
            generation, contact import, and launch.
          </p>
          <button
            disabled
            title="Campaign wizard — coming soon"
            className="px-5 py-2 rounded-lg bg-indigo-600 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Create Campaign (coming soon)
          </button>
        </div>
      </div>
    </div>
  );
}
