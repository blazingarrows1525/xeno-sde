"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Megaphone, Sparkles, LogOut, Menu, X } from "lucide-react";
import { Tip } from "@/components/ui";
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
  const [open, setOpen] = useState(false);

  // Close the mobile drawer whenever the route changes.
  useEffect(() => {
    setOpen(false);
  }, [path]);

  // The login screen is full-bleed — no sidebar chrome.
  if (path === "/login") return <>{children}</>;

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      {/* Mobile top bar — hidden on lg where the rail is always visible */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-white/[0.06] bg-zinc-950/70 px-4 py-3 backdrop-blur-xl lg:hidden">
        <button
          onClick={() => setOpen(true)}
          aria-label="Open menu"
          className="btn-tactile grid h-9 w-9 place-items-center rounded-lg border border-white/[0.08] text-slate-300 hover:bg-white/[0.05]"
        >
          <Menu size={18} />
        </button>
        <div className="flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 text-sm font-bold text-white shadow-lg shadow-emerald-500/30">
            K
          </div>
          <span className="font-semibold tracking-tight text-slate-100">Kairos</span>
        </div>
        <div className="h-9 w-9" aria-hidden />
      </header>

      {/* Dimming overlay behind the drawer (mobile only) */}
      {open ? (
        <div
          onClick={() => setOpen(false)}
          className="animate-fade fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          aria-hidden
        />
      ) : null}

      {/* Sidebar — slide-out drawer on mobile, static rail on desktop.
          The slide transform is scoped to max-lg: so at the lg breakpoint no transform utility
          applies at all (a clean static rail), and below lg it animates the plain `transform`
          property with literal values — Tailwind v4's translate-x utilities drive the CSS
          `translate` longhand via an @property variable, which we avoid here. */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex h-full w-64 shrink-0 flex-col gap-1 border-r border-white/[0.06] bg-zinc-950/90 p-4 backdrop-blur-xl transition-transform duration-300 ease-out lg:sticky lg:top-0 lg:z-auto lg:h-screen lg:bg-white/[0.02] ${
          open ? "max-lg:[transform:translateX(0px)]" : "max-lg:[transform:translateX(-100%)]"
        }`}
      >
        {/* brand */}
        <div className="mb-6 flex items-center justify-between px-2 py-2">
          <div className="flex items-center gap-3">
            <div className="relative grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 text-lg font-bold text-white shadow-lg shadow-emerald-500/40">
              K
              <span className="absolute inset-0 -z-10 rounded-xl bg-emerald-500/40 blur-md" />
            </div>
            <div>
              <div className="font-semibold leading-tight tracking-tight text-slate-100">Kairos</div>
              <div className="text-[11px] leading-tight text-slate-500">autonomous growth</div>
            </div>
          </div>
          {/* close (mobile only) */}
          <button
            onClick={() => setOpen(false)}
            aria-label="Close menu"
            className="btn-tactile grid h-8 w-8 place-items-center rounded-lg text-slate-400 hover:bg-white/[0.05] hover:text-slate-200 lg:hidden"
          >
            <X size={18} />
          </button>
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
                  ? "bg-gradient-to-r from-emerald-500/20 to-teal-500/[0.06] text-white shadow-[inset_0_1px_0_0_rgba(255,255,255,0.06)]"
                  : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-200"
              }`}
            >
              {active ? (
                <span className="nav-indicator absolute left-0 top-1/2 h-5 w-0.5 rounded-r bg-gradient-to-b from-emerald-400 to-teal-400" />
              ) : null}
              <Icon
                size={18}
                className={`transition-transform duration-200 group-hover:[transform:translateX(2px)] ${
                  active ? "text-emerald-300" : "text-slate-500 group-hover:text-slate-300"
                }`}
              />
              {label}
            </Link>
          );
        })}

        <div className="mt-auto space-y-3">
          {user ? (
            <div className="rounded-xl border border-white/[0.07] bg-white/[0.03] p-2.5 backdrop-blur-xl">
              <div className="flex items-center gap-2.5">
                <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 text-xs font-semibold text-white">
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
                <Tip className="w-full" tip="Ends this session and returns to the sign-in screen.">
                  <button className="btn-tactile mt-2 flex w-full items-center justify-center gap-1.5 rounded-lg border border-white/[0.08] px-2 py-1.5 text-[11px] text-slate-400 hover:border-white/[0.16] hover:text-slate-200">
                    <LogOut size={12} /> Sign out
                  </button>
                </Tip>
              </form>
            </div>
          ) : null}
          <div className="px-2 text-[11px] text-slate-600">© 2026 Kairos</div>
        </div>
      </aside>

      <main className="min-w-0 flex-1">{children}</main>
    </div>
  );
}
