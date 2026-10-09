"use client";

import { useState } from "react";
import Link from "next/link";

const STATUSES = ["All", "Draft", "Scheduled", "Running", "Complete", "Failed", "Cancelled"] as const;

export default function CampaignFilters() {
  const [activeTab, setActiveTab] = useState<string>("All");
  const [query, setQuery] = useState("");

  return (
    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-stone-200 pb-4">
      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-1">
        {STATUSES.map((status) => {
          const isActive = activeTab === status;
          return (
            <button
              key={status}
              type="button"
              onClick={() => setActiveTab(status)}
              className={`btn-3d px-3 py-1.5 text-xs font-mono rounded-md uppercase tracking-wider transition-all duration-150 ${
                isActive
                  ? "bg-stone-900 !text-white font-bold shadow-md transform -translate-y-0.5"
                  : "bg-stone-100 text-stone-700 hover:bg-stone-200 hover:text-stone-900 font-medium"
              }`}
            >
              {status}
            </button>
          );
        })}
      </div>

      {/* Right controls: Search & New Campaign */}
      <div className="flex items-center gap-3">
        <div className="relative">
          <input
            type="text"
            placeholder="Filter campaigns..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-48 sm:w-64 px-3 py-1.5 text-xs font-mono bg-white border border-stone-300 rounded-md placeholder-stone-400 focus:outline-none focus:ring-1 focus:ring-stone-900 focus:border-stone-900"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-700 text-xs"
            >
              &times;
            </button>
          )}
        </div>

        <Link
          href="/campaigns/new"
          className="btn-3d inline-flex items-center gap-1.5 px-4 py-2 text-xs font-mono font-bold uppercase tracking-wider bg-stone-900 hover:bg-stone-800 !text-white rounded-md transition-colors shadow-md hover:shadow-lg"
        >
          <span className="text-sm leading-none">+</span> New Campaign
        </Link>
      </div>
    </div>
  );
}
