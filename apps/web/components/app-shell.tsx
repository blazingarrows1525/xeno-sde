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
      <aside className="sticky top-0 flex h-screen w-64 shrink-0 flex-col gap-1 border-r border-white/[0.06] bg-white/[0.02] p-4 backdrop-blur-xl">
        {/* brand */}
        <div className="mb-6 flex items-center gap-3 px-2 py-2">
          <div className="relative grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-lg font-bold text-white shadow-lg shadow-indigo-500/40">
            K
            <span className="absolute inset-0 -z-10 rounded-xl bg-indigo-500/40 blur-md" />
          </div>
          <div>
            <div className="font-semibold leading-tight tracking-tight text-slate-100">Kairos</div>
            <div className="text-[11px] leading-tight text-slate-500">autonomous growth</div>
          </div>
        </div>

        <div className="px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-600">
          Workspace
        </div>

        {NAV.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? path === "/" : path.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
                active
                  ? "bg-gradient-to-r from-indigo-500/20 to-violet-500/[0.06] text-white shadow-[inset_0_1px_0_0_rgba(255,255,255,0.06)]"
                  : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-200"
              }`}
            >
              {active ? (
                <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r bg-gradient-to-b from-indigo-400 to-violet-400" />
              ) : null}
              <Icon
                size={18}
                className={active ? "text-indigo-300" : "text-slate-500 group-hover:text-slate-300"}
              />
              {label}
            </Link>
          );
        })}

        <div className="mt-auto space-y-3">
          {user ? (
            <div className="rounded-xl border border-white/[0.07] bg-white/[0.03] p-2.5 backdrop-blur-xl">
              <div className="flex items-center gap-2.5">
                <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 text-xs font-semibold text-white">
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
                <button className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-lg border border-white/[0.08] px-2 py-1.5 text-[11px] text-slate-400 transition hover:border-white/[0.16] hover:text-slate-200">
                  <LogOut size={12} /> Sign out
                </button>
              </form>
            </div>
          ) : null}
          <div className="px-2 text-[11px] text-slate-600">Xeno take-home · 2026</div>
        </div>
      </aside>
      <main className="min-w-0 flex-1">{children}</main>
    </div>
  );
}
