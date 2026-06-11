import Link from "next/link";
import { Sparkles, ArrowRight } from "lucide-react";
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

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ e?: string; from?: string }>;
}) {
  const sp = await searchParams;
  const error = sp.e ? ERRORS[sp.e] ?? "Something went wrong. Try the demo workspace." : null;

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-950 px-4">
      {/* animated ambient glow */}
      <div className="pointer-events-none absolute -top-32 -left-24 h-96 w-96 rounded-full bg-indigo-600/30 blur-3xl animate-pulse" />
      <div className="pointer-events-none absolute -bottom-32 -right-16 h-96 w-96 rounded-full bg-emerald-500/20 blur-3xl animate-pulse [animation-delay:1.2s]" />
      <div className="pointer-events-none absolute top-1/3 left-1/2 h-72 w-72 -translate-x-1/2 rounded-full bg-fuchsia-600/10 blur-3xl animate-pulse [animation-delay:.6s]" />

      <div className="relative grid w-full max-w-4xl overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 shadow-2xl backdrop-blur md:grid-cols-2">
        {/* brand panel */}
        <div className="hidden flex-col justify-between border-r border-slate-800 bg-gradient-to-br from-indigo-600/15 via-slate-900/0 to-emerald-500/10 p-8 md:flex">
          <div className="flex items-center gap-2">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-indigo-500 text-lg font-bold text-white shadow-lg shadow-indigo-500/30">
              K
            </div>
            <div>
              <div className="font-semibold leading-tight text-slate-100">Kairos</div>
              <div className="text-xs leading-tight text-slate-400">autonomous growth</div>
            </div>
          </div>

          <div className="space-y-4">
            <h2 className="text-2xl font-semibold leading-tight text-slate-100">
              The AI marketer that<br />reasons in the open.
            </h2>
            <ul className="space-y-2 text-sm text-slate-400">
              <li className="flex items-center gap-2"><Sparkles size={15} className="text-indigo-400" /> State a goal — watch it plan, live.</li>
              <li className="flex items-center gap-2"><ShieldIcon /> Every launch waits for your approval.</li>
              <li className="flex items-center gap-2"><ArrowRight size={15} className="text-fuchsia-400" /> Predictions that calibrate over time.</li>
            </ul>
          </div>

          <div className="text-xs text-slate-600">Xeno Engineering Take-Home · 2026</div>
        </div>

        {/* sign-in panel */}
        <div className="flex flex-col justify-center gap-5 p-6 sm:p-8">
          <div className="md:hidden flex items-center gap-2">
            <div className="grid h-9 w-9 place-items-center rounded-lg bg-indigo-500 font-bold text-white">K</div>
            <span className="font-semibold text-slate-100">Kairos</span>
          </div>

          <div>
            <h1 className="text-xl font-semibold text-slate-100">Welcome back</h1>
            <p className="mt-1 text-sm text-slate-400">Sign in to open the agent console.</p>
          </div>

          {error ? (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
              {error}
            </div>
          ) : null}

          <div className="space-y-2.5">
            <Link
              href="/api/auth/start/google"
              className="flex w-full items-center justify-center gap-3 rounded-lg border border-slate-700 bg-slate-800/60 px-4 py-2.5 text-sm font-medium text-slate-100 transition hover:border-slate-600 hover:bg-slate-800"
            >
              <GoogleIcon /> Continue with Google
            </Link>
            <Link
              href="/api/auth/start/github"
              className="flex w-full items-center justify-center gap-3 rounded-lg border border-slate-700 bg-slate-800/60 px-4 py-2.5 text-sm font-medium text-slate-100 transition hover:border-slate-600 hover:bg-slate-800"
            >
              <GithubIcon /> Continue with GitHub
            </Link>
          </div>

          <div className="flex items-center gap-3 text-xs text-slate-600">
            <div className="h-px flex-1 bg-slate-800" />
            or
            <div className="h-px flex-1 bg-slate-800" />
          </div>

          {/* Always-available demo entry — keeps the live deployment reviewable. */}
          <form action="/api/auth/demo" method="post">
            <button
              type="submit"
              className="group flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-400"
            >
              Enter demo workspace
              <ArrowRight size={16} className="transition group-hover:translate-x-0.5" />
            </button>
          </form>

          <p className="text-center text-[11px] text-slate-500">
            {providers.google || providers.github
              ? "OAuth is live. The demo workspace needs no account."
              : "No account needed — the demo workspace opens the full app."}
          </p>
        </div>
      </div>
    </div>
  );
}
