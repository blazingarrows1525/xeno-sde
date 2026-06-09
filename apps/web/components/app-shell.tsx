"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Megaphone, Sparkles } from "lucide-react";

const NAV = [
  { href: "/", label: "Agent Console", icon: Sparkles },
  { href: "/campaigns", label: "Campaigns", icon: Megaphone },
  { href: "/insights", label: "Insights", icon: BarChart3 },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  return (
    <div className="flex min-h-screen">
      <aside className="flex w-64 shrink-0 flex-col gap-1 border-r border-slate-800 bg-slate-900/40 p-4">
        <div className="mb-3 flex items-center gap-2 px-2 py-2">
          <div className="grid h-9 w-9 place-items-center rounded-lg bg-indigo-500 font-bold text-white">
            K
          </div>
          <div>
            <div className="font-semibold leading-tight">Kairos</div>
            <div className="text-xs leading-tight text-slate-400">autonomous growth</div>
          </div>
        </div>
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? path === "/" : path.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
                active
                  ? "bg-indigo-500/15 text-indigo-300"
                  : "text-slate-300 hover:bg-slate-800/60"
              }`}
            >
              <Icon size={18} />
              {label}
            </Link>
          );
        })}
        <div className="mt-auto px-2 text-xs text-slate-500">Xeno take-home</div>
      </aside>
      <main className="min-w-0 flex-1">{children}</main>
    </div>
  );
}
