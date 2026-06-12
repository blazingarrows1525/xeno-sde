import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";
import { CountUp } from "./count-up";

type ButtonVariant = "primary" | "ghost" | "success";

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary:
    "sheen bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50 hover:brightness-110",
  ghost:
    "border border-white/[0.08] bg-white/[0.03] text-slate-200 hover:border-white/[0.18] hover:bg-white/[0.06]",
  success: "bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25",
};

export function Button({
  children,
  variant = "primary",
  loading = false,
  fullWidth = false,
  className = "",
  disabled,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  loading?: boolean;
  fullWidth?: boolean;
}) {
  return (
    <button
      disabled={disabled || loading}
      className={`btn-tactile inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold disabled:pointer-events-none disabled:opacity-55 ${
        BUTTON_VARIANTS[variant]
      } ${fullWidth ? "w-full" : ""} ${className}`}
      {...rest}
    >
      {loading ? <Loader2 size={16} className="animate-spin" /> : null}
      {children}
    </button>
  );
}

/** Wraps a control with a hover/focus tooltip that explains what it does. */
export function Tip({
  tip,
  children,
  className = "",
}: {
  tip: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span className={`tip-wrap inline-flex ${className}`}>
      {children}
      <span role="tooltip" className="tip-bubble">
        {tip}
      </span>
    </span>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden className={`skeleton rounded-lg ${className}`} />;
}

/** Loading placeholder shaped like a bar chart, so charts don't pop in from nothing. */
export function ChartSkeleton({ height = 260 }: { height?: number }) {
  const bars = [42, 68, 55, 82, 60, 90, 72, 48];
  return (
    <div aria-hidden style={{ height }} className="flex items-end gap-3 px-2 pb-2">
      {bars.map((h, i) => (
        <div
          key={i}
          className="skeleton w-full rounded-t-md"
          style={{ height: `${h}%`, animationDelay: `${i * 90}ms` }}
        />
      ))}
    </div>
  );
}

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
    indigo: "bg-sky-500/15 text-sky-300 ring-1 ring-inset ring-sky-500/25",
    red: "bg-red-500/15 text-red-300 ring-1 ring-inset ring-red-500/20",
    violet: "bg-teal-500/15 text-teal-300 ring-1 ring-inset ring-teal-500/25",
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
    <div className="flex items-start justify-between gap-4 border-b border-white/[0.06] px-4 py-5 sm:px-6 lg:px-8 lg:py-6">
      <div className="animate-fade-up min-w-0">
        <h1 className="text-xl font-semibold tracking-tight text-gradient sm:text-2xl">{title}</h1>
        {subtitle ? <p className="mt-1.5 text-sm text-slate-400">{subtitle}</p> : null}
      </div>
      {actions ? <div className="shrink-0">{actions}</div> : null}
    </div>
  );
}
