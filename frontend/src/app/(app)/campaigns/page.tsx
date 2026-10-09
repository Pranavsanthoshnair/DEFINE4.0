import type { Metadata } from "next";
import Link from "next/link";
import PageHeader from "@/components/ui/PageHeader";
import CampaignFilters from "@/components/ui/interactive/CampaignFilters";

export const metadata: Metadata = { title: "Campaigns - Veylo" };

export default function CampaignsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Campaigns"
        subtitle="Manage, schedule, and track multilingual outbound calling campaigns."
      />

      <CampaignFilters />

      {/* Campaigns Table or Empty State */}
      <div className="bg-white rounded-xl border border-stone-200 overflow-hidden shadow-sm">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-stone-50 border-b border-stone-200 text-[11px] font-mono text-stone-500 uppercase tracking-wider">
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4">Campaign Name</th>
              <th className="py-3 px-4">Languages</th>
              <th className="py-3 px-4">Recipients</th>
              <th className="py-3 px-4">Success Rate</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100 text-xs font-sans">
            <tr className="hover:bg-stone-50/60 transition-colors">
              <td className="py-3 px-4 font-mono">
                <span className="inline-flex items-center gap-1.5 text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded text-[10px] font-semibold border border-emerald-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                  RUNNING
                </span>
              </td>
              <td className="py-3 px-4 font-medium text-stone-900">
                Annual Tech Summit 2026 VIP Invite
              </td>
              <td className="py-3 px-4 font-mono text-stone-600">Hindi, Tamil, English</td>
              <td className="py-3 px-4 font-mono text-stone-600">2,450</td>
              <td className="py-3 px-4 font-mono text-stone-600">84.2%</td>
              <td className="py-3 px-4 text-right font-mono">
                <a href="/campaigns/demo-1" className="text-brand-red hover:underline font-semibold">
                  View Live &rarr;
                </a>
              </td>
            </tr>
            <tr className="hover:bg-stone-50/60 transition-colors">
              <td className="py-3 px-4 font-mono">
                <span className="inline-flex items-center gap-1.5 text-stone-700 bg-stone-100 px-2 py-0.5 rounded text-[10px] font-semibold border border-stone-200">
                  COMPLETED
                </span>
              </td>
              <td className="py-3 px-4 font-medium text-stone-900">
                Keynote RSVP Confirmation Wave 1
              </td>
              <td className="py-3 px-4 font-mono text-stone-600">Hindi, English</td>
              <td className="py-3 px-4 font-mono text-stone-600">1,200</td>
              <td className="py-3 px-4 font-mono text-stone-600">91.8%</td>
              <td className="py-3 px-4 text-right font-mono">
                <a href="/campaigns/demo-2" className="text-stone-600 hover:text-stone-900 font-semibold">
                  Report &rarr;
                </a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
