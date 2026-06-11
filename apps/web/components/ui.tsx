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
      className={`surface rounded-2xl ${hover ? "card-hover" : ""} ${
        animate ? "animate-fade-up" : ""
      } ${className}`}
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
  icon,
}: {
  label: string;
  value?: ReactNode;
  sub?: ReactNode;
  to?: number;
  format?: (n: number) => string;
  icon?: ReactNode;
}) {
  return (
    <div className="p-5">
      <div className="flex items-center justify-between">
        <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
        {icon ? <span className="text-slate-500">{icon}</span> : null}
      </div>
      <div className="mt-2 text-[26px] font-semibold leading-none text-slate-100 tabular-nums tracking-tight">
        {typeof to === "number" ? <CountUp to={to} format={format} /> : value}
      </div>
      {sub ? <div className="mt-1.5 text-xs text-slate-400">{sub}</div> : null}
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
    slate: "bg-white/[0.06] text-slate-300 ring-1 ring-inset ring-white/[0.08]",
    green: "bg-emerald-500/15 text-emerald-300 ring-1 ring-inset ring-emerald-500/20",
    amber: "bg-amber-500/15 text-amber-300 ring-1 ring-inset ring-amber-500/20",
    indigo: "bg-indigo-500/15 text-indigo-300 ring-1 ring-inset ring-indigo-500/25",
    red: "bg-red-500/15 text-red-300 ring-1 ring-inset ring-red-500/20",
    violet: "bg-violet-500/15 text-violet-300 ring-1 ring-inset ring-violet-500/25",
  };
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}
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
    <div className="flex items-start justify-between gap-4 border-b border-white/[0.06] px-8 py-6">
      <div className="animate-fade-up">
        <h1 className="text-2xl font-semibold tracking-tight text-gradient">{title}</h1>
        {subtitle ? <p className="mt-1.5 text-sm text-slate-400">{subtitle}</p> : null}
      </div>
      {actions}
    </div>
  );
}
