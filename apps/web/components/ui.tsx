import type { ReactNode } from "react";
import { CountUp } from "./count-up";

export function Card({
  children,
  className = "",
  delay = 0,
  hover = true,
  animate = true,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
  hover?: boolean;
  animate?: boolean;
}) {
  return (
    <div
      style={delay ? { animationDelay: `${delay}ms` } : undefined}
      className={`rounded-xl border border-slate-800 bg-slate-900/50 ${
        hover ? "card-hover" : ""
      } ${animate ? "animate-fade-up" : ""} ${className}`}
    >
      {children}
    </div>
  );
}

export function Stat({
  label,
  value,
  sub,
  to,
  format,
}: {
  label: string;
  value?: ReactNode;
  sub?: ReactNode;
  to?: number;
  format?: (n: number) => string;
}) {
  return (
    <div className="p-4">
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-100 tabular-nums">
        {typeof to === "number" ? <CountUp to={to} format={format} /> : value}
      </div>
      {sub ? <div className="mt-0.5 text-xs text-slate-400">{sub}</div> : null}
    </div>
  );
}

type Tone = "slate" | "green" | "amber" | "indigo" | "red" | "violet";

export function Badge({
  children,
  tone = "slate",
  pulse = false,
}: {
  children: ReactNode;
  tone?: Tone;
  pulse?: boolean;
}) {
  const tones: Record<Tone, string> = {
    slate: "bg-slate-700/40 text-slate-300",
    green: "bg-emerald-500/15 text-emerald-300",
    amber: "bg-amber-500/15 text-amber-300",
    indigo: "bg-indigo-500/15 text-indigo-300",
    red: "bg-red-500/15 text-red-300",
    violet: "bg-violet-500/15 text-violet-300",
  };
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${tones[tone]}`}
    >
      {pulse ? <span className="live-dot" /> : null}
      {children}
    </span>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-800 px-8 py-6">
      <div className="animate-fade-up">
        <h1 className="text-xl font-semibold text-slate-100">{title}</h1>
        {subtitle ? <p className="mt-1 text-sm text-slate-400">{subtitle}</p> : null}
      </div>
      {actions}
    </div>
  );
}
