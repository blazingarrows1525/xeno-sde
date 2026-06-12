import Link from "next/link";
import { ArrowRight, CheckCircle2, Sparkles, Wrench } from "lucide-react";
import { providers } from "@/lib/auth";

const ERRORS: Record<string, string> = {
  google_unconfigured: "Google sign-in isn't configured for this deployment — jump in with the demo workspace.",
  github_unconfigured: "GitHub sign-in isn't configured for this deployment — jump in with the demo workspace.",
  google_failed: "Google sign-in didn't complete. Try again, or use the demo workspace.",
  github_failed: "GitHub sign-in didn't complete. Try again, or use the demo workspace.",
  cancelled: "Sign-in was cancelled.",
};

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden>
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3c-1.6 4.7-6.1 8-11.3 8a12 12 0 1 1 7.9-21l5.7-5.7A20 20 0 1 0 24 44a20 20 0 0 0 19.6-23.5z" />
      <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8A12 12 0 0 1 24 12c3.1 0 5.9 1.2 8 3.1l5.7-5.7A20 20 0 0 0 6.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2A12 12 0 0 1 12.7 28l-6.6 5.1A20 20 0 0 0 24 44z" />
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3a12 12 0 0 1-4.1 5.6l6.2 5.2C39.9 35.7 44 30.5 44 24c0-1.2-.1-2.4-.4-3.5z" />
    </svg>
  );
}

function GithubIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M12 .5A11.5 11.5 0 0 0 .5 12a11.5 11.5 0 0 0 7.86 10.92c.575.106.785-.25.785-.555 0-.274-.01-1.0-.015-1.96-3.2.695-3.875-1.543-3.875-1.543-.523-1.33-1.278-1.683-1.278-1.683-1.044-.714.08-.699.08-.699 1.155.081 1.763 1.186 1.763 1.186 1.027 1.76 2.695 1.251 3.35.957.105-.744.402-1.252.732-1.54-2.555-.29-5.243-1.278-5.243-5.685 0-1.256.448-2.283 1.183-3.088-.119-.29-.513-1.46.112-3.045 0 0 .966-.31 3.165 1.18a10.96 10.96 0 0 1 2.88-.388c.977.004 1.96.132 2.88.388 2.197-1.49 3.162-1.18 3.162-1.18.626 1.585.232 2.755.114 3.045.737.805 1.18 1.832 1.18 3.088 0 4.418-2.692 5.392-5.255 5.677.413.355.78 1.057.78 2.13 0 1.538-.014 2.778-.014 3.156 0 .308.207.667.79.554A11.5 11.5 0 0 0 23.5 12 11.5 11.5 0 0 0 12 .5Z" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg
      width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      className="text-emerald-400" aria-hidden
    >
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}

// A miniature of the real reasoning trace — the product demos itself on the door.
const PREVIEW_STEPS = [
  {
    icon: <Wrench size={13} />,
    ring: "bg-indigo-500/15 text-indigo-300",
    title: "segment.preview",
    mono: true,
    detail: "inactive_days > 60 AND lifetime_spend ≥ 8000",
  },
  {
    icon: <CheckCircle2 size={13} />,
    ring: "bg-emerald-500/15 text-emerald-300",
    title: "1,284 customers match",
    detail: "compiled to parameterized SQL",
  },
  {
    icon: <Sparkles size={13} />,
    ring: "bg-violet-500/15 text-violet-300",
    title: "Plan ready — 3.2× predicted ROAS",
    detail: "held for your approval",
  },
];

function TracePreview() {
  return (
    <div className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-3 backdrop-blur-xl">
      <div className="mb-2.5 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">
          Live reasoning trace
        </span>
        <span className="live-dot" />
      </div>
      <ol className="space-y-1.5">
        {PREVIEW_STEPS.map((s, i) => (
          <li
            key={i}
            style={{ animationDelay: `${0.6 + i * 0.55}s` }}
            className="animate-slide-in flex items-start gap-2.5 rounded-lg border border-white/[0.05] bg-white/[0.02] px-2.5 py-1.5"
          >
            <span className={`mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-md ${s.ring}`}>
              {s.icon}
            </span>
            <span className="min-w-0">
              <span
                className={`block truncate text-xs ${
                  s.mono ? "font-mono text-indigo-300" : "font-medium text-slate-200"
                }`}
              >
                {s.title}
              </span>
              <span className="block truncate text-[11px] text-slate-500">{s.detail}</span>
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ e?: string; from?: string }>;
}) {
  const sp = await searchParams;
  const error = sp.e ? ERRORS[sp.e] ?? "Something went wrong. Try the demo workspace." : null;

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-10">
      {/* calm ambient accents over the global aurora */}
      <div aria-hidden className="pointer-events-none absolute -top-40 left-1/2 h-[26rem] w-[42rem] -translate-x-1/2 rounded-full bg-indigo-600/15 blur-3xl" />
      <div aria-hidden className="animate-float pointer-events-none absolute -bottom-32 -right-20 h-80 w-80 rounded-full bg-emerald-500/10 blur-3xl" />
      <div
        aria-hidden
        className="animate-float pointer-events-none absolute -left-24 top-1/3 h-72 w-72 rounded-full bg-violet-600/10 blur-3xl"
        style={{ animationDelay: "3s" }}
      />

      {/* gradient hairline frame */}
      <div className="animate-scale-in relative w-full max-w-4xl rounded-3xl bg-gradient-to-br from-white/[0.14] via-white/[0.04] to-white/[0.1] p-px shadow-2xl shadow-black/60">
        <div className="grid overflow-hidden rounded-[calc(1.5rem-1px)] bg-[#090b18]/90 backdrop-blur-2xl md:grid-cols-2">
          {/* brand panel */}
          <div className="hidden flex-col justify-between gap-8 border-r border-white/[0.06] bg-gradient-to-br from-indigo-600/[0.12] via-transparent to-emerald-500/[0.08] p-8 md:flex">
            <div className="flex items-center gap-3">
              <div className="relative grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-lg font-bold text-white shadow-lg shadow-indigo-500/40">
                K
                <span aria-hidden className="absolute inset-0 -z-10 rounded-xl bg-indigo-500/40 blur-md" />
              </div>
              <div>
                <div className="font-semibold leading-tight tracking-tight text-slate-100">Kairos</div>
                <div className="text-xs leading-tight text-slate-500">autonomous growth</div>
              </div>
            </div>

            <div className="space-y-5">
              <h2 className="text-balance text-2xl font-semibold leading-tight tracking-tight text-slate-100">
                The AI marketer that <span className="text-gradient">reasons in the open.</span>
              </h2>
              <TracePreview />
              <ul className="space-y-2 text-sm text-slate-400">
                <li className="flex items-center gap-2">
                  <ShieldIcon /> Every launch waits for your approval.
                </li>
                <li className="flex items-center gap-2">
                  <ArrowRight size={15} className="text-fuchsia-400" /> Predictions that calibrate over time.
                </li>
              </ul>
            </div>

            <div className="text-xs text-slate-600">Xeno Engineering Take-Home · 2026</div>
          </div>

          {/* sign-in panel */}
          <div className="flex flex-col justify-center gap-5 p-6 sm:p-8">
            <div className="flex items-center gap-2.5 md:hidden">
              <div className="grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 font-bold text-white shadow-lg shadow-indigo-500/30">
                K
              </div>
              <span className="font-semibold tracking-tight text-slate-100">Kairos</span>
            </div>

            <div className="animate-fade-up" style={{ animationDelay: "80ms" }}>
              <h1 className="text-xl font-semibold tracking-tight text-slate-100">Welcome back</h1>
              <p className="mt-1 text-sm text-slate-400">Sign in to open the agent console.</p>
            </div>

            {error ? (
              <div className="animate-fade-up rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs leading-relaxed text-amber-300">
                {error}
              </div>
            ) : null}

            <div className="animate-fade-up space-y-2.5" style={{ animationDelay: "140ms" }}>
              <Link
                href="/api/auth/start/google"
                className="flex w-full items-center justify-center gap-3 rounded-xl border border-white/[0.08] bg-white/[0.03] px-4 py-2.5 text-sm font-medium text-slate-100 transition hover:border-white/[0.18] hover:bg-white/[0.06] active:scale-[0.99]"
              >
                <GoogleIcon /> Continue with Google
              </Link>
              <Link
                href="/api/auth/start/github"
                className="flex w-full items-center justify-center gap-3 rounded-xl border border-white/[0.08] bg-white/[0.03] px-4 py-2.5 text-sm font-medium text-slate-100 transition hover:border-white/[0.18] hover:bg-white/[0.06] active:scale-[0.99]"
              >
                <GithubIcon /> Continue with GitHub
              </Link>
            </div>

            <div
              className="animate-fade-up flex items-center gap-3 text-xs text-slate-600"
              style={{ animationDelay: "200ms" }}
            >
              <div className="h-px flex-1 bg-white/[0.07]" />
              or
              <div className="h-px flex-1 bg-white/[0.07]" />
            </div>

            {/* Always-available demo entry — keeps the live deployment reviewable. */}
            <form action="/api/auth/demo" method="post" className="animate-fade-up" style={{ animationDelay: "260ms" }}>
              <button
                type="submit"
                className="sheen group flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-500/30 transition hover:shadow-indigo-500/50 hover:brightness-110 active:scale-[0.99]"
              >
                Enter demo workspace
                <ArrowRight
                  size={16}
                  className="transition-transform group-hover:[transform:translateX(3px)]"
                />
              </button>
            </form>

            <p
              className="animate-fade-up text-center text-[11px] text-slate-500"
              style={{ animationDelay: "320ms" }}
            >
              {providers.google || providers.github
                ? "OAuth is live. The demo workspace needs no account."
                : "No account needed — the demo workspace opens the full app."}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
