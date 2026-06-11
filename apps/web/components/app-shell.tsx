"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Megaphone, Sparkles, LogOut } from "lucide-react";
import type { SessionUser } from "@/lib/auth";

const NAV = [
  { href: "/", label: "Agent Console", icon: Sparkles },
  { href: "/campaigns", label: "Campaigns", icon: Megaphone },
  { href: "/insights", label: "Insights", icon: BarChart3 },
];

export function AppShell({
  children,
  user,
}: {
  children: React.ReactNode;
  user?: SessionUser | null;
}) {
  const path = usePathname();
  // The login screen is full-bleed — no sidebar chrome.
  if (path === "/login") return <>{children}</>;
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
        <div className="mt-auto space-y-2">
          {user ? (
            <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-2">
              <div className="flex items-center gap-2">
                <div className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-indigo-500/20 text-xs font-semibold text-indigo-300">
                  {user.name?.[0]?.toUpperCase() ?? "U"}
                </div>
                <div className="min-w-0">
                  <div className="truncate text-xs font-medium text-slate-200">{user.name}</div>
                  <div className="truncate text-[10px] text-slate-500">
                    {user.provider === "demo" ? "demo workspace" : user.email}
                  </div>
                </div>
              </div>
              <form action="/api/auth/logout" method="post">
                <button className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-md border border-slate-700 px-2 py-1 text-[11px] text-slate-400 transition hover:border-slate-600 hover:text-slate-200">
                  <LogOut size={12} /> Sign out
                </button>
              </form>
            </div>
          ) : null}
          <div className="px-2 text-xs text-slate-500">Xeno take-home</div>
        </div>
      </aside>
      <main className="min-w-0 flex-1">{children}</main>
    </div>
  );
}
