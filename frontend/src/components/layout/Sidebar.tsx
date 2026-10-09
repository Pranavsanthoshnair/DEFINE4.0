import Link from "next/link";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: "⊞" },
  { href: "/campaigns", label: "Campaigns", icon: "📣" },
  { href: "/contacts", label: "Contacts", icon: "👥" },
  { href: "/analytics", label: "Analytics", icon: "📊" },
];

export default function Sidebar() {
  return (
    <aside className="w-56 shrink-0 border-r border-gray-800 bg-gray-900 flex flex-col min-h-screen">
      <div className="px-5 py-5 border-b border-gray-800">
        <span className="text-lg font-bold tracking-tight gradient-text">
          Veylo
        </span>
      </div>
      <nav className="flex-1 px-3 py-4 flex flex-col gap-1">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
          >
            <span>{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="px-5 py-4 border-t border-gray-800 text-xs text-gray-600">
        Veylo v0.1 · DEFINE 4.0
      </div>
    </aside>
  );
}
