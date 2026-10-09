import type { Metadata } from "next";
import Sidebar from "@/components/layout/Sidebar";

export const metadata: Metadata = { title: "Contacts — Veylo" };

export default function ContactsPage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Contacts</h1>
            <p className="text-gray-400 text-sm mt-0.5">
              Import and manage contact lists
            </p>
          </div>
          <button
            disabled
            className="px-4 py-2 rounded-lg bg-indigo-600 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Import CSV
          </button>
        </div>

        {/* Upload zone stub */}
        <div className="glass border-2 border-dashed border-gray-700 rounded-xl p-12 flex flex-col items-center text-center gap-3">
          <span className="text-4xl">📤</span>
          <h2 className="font-semibold">Upload a contacts CSV</h2>
          <p className="text-gray-400 text-sm max-w-sm">
            Columns: <code className="text-indigo-300">name</code>,{" "}
            <code className="text-indigo-300">phone</code>,{" "}
            <code className="text-indigo-300">language</code> (optional).
            Phone numbers will be validated before import.
          </p>
          <button
            disabled
            className="mt-2 px-5 py-2 rounded-lg bg-gray-700 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Choose file (coming soon)
          </button>
        </div>
      </div>
    </div>
  );
}
