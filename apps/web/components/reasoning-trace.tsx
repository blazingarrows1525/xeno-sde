import { Brain, CheckCircle2, FileText, Sparkles, Wrench } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { AgentStep } from "@/lib/types";

const META: Record<AgentStep["kind"], { icon: LucideIcon; tone: string; ring: string }> = {
  thought: { icon: Brain, tone: "text-sky-300", ring: "bg-sky-500/15" },
  tool_call: { icon: Wrench, tone: "text-cyan-300", ring: "bg-cyan-500/15" },
  tool_result: { icon: CheckCircle2, tone: "text-emerald-300", ring: "bg-emerald-500/15" },
  plan: { icon: FileText, tone: "text-amber-300", ring: "bg-amber-500/15" },
  final: { icon: Sparkles, tone: "text-teal-300", ring: "bg-teal-500/15" },
};

function Thinking({ label, boxed = false }: { label: string; boxed?: boolean }) {
  return (
    <div
      className={`flex items-center gap-3 ${
        boxed ? "rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2" : ""
      }`}
    >
      <span className="flex gap-1">
        {[0, 1, 2].map((d) => (
          <span
            key={d}
            className="h-1.5 w-1.5 rounded-full bg-emerald-400"
            style={{ animation: `thinkingDot 1.2s ${d * 0.16}s infinite ease-in-out` }}
          />
        ))}
      </span>
      <span className="text-sm text-slate-400">{label}</span>
    </div>
  );
}

export function ReasoningTrace({
  steps,
  running = false,
}: {
  steps: AgentStep[];
  running?: boolean;
}) {
  if (steps.length === 0) {
    return running ? (
      <Thinking label="Reading your goal and analysing the shopper base…" />
    ) : (
      <div className="grid place-items-center gap-2 rounded-xl border border-dashed border-white/[0.08] px-6 py-10 text-center">
        <span className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-500/10 text-emerald-300">
          <Brain size={18} />
        </span>
        <p className="text-sm text-slate-400">
          {"The agent's reasoning streams here, step by step."}
        </p>
        <p className="text-xs text-slate-600">
          Every tool call, segment query and decision — fully inspectable.
        </p>
      </div>
    );
  }
  return (
    <ol className="space-y-2">
      {steps.map((step, i) => {
        const meta = META[step.kind];
        const Icon = meta.icon;
        return (
          <li
            key={i}
            style={{ animationDelay: `${Math.min(i, 6) * 40}ms` }}
            className="trace-item flex gap-3 rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 transition-colors hover:border-white/[0.12]"
          >
            <span
              className={`mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-md ${meta.ring}`}
            >
              <Icon size={14} className={meta.tone} />
            </span>
            <div className="min-w-0">
              <div className="text-sm">
                {step.tool ? (
                  <span className="font-mono text-xs text-teal-300">{step.tool}</span>
                ) : (
                  <span className="font-medium text-slate-200">{step.title}</span>
                )}
                {step.tool ? <span className="ml-2 text-slate-300">{step.title}</span> : null}
              </div>
              {step.detail ? (
                <div className="mt-0.5 text-xs text-slate-400">{step.detail}</div>
              ) : null}
            </div>
          </li>
        );
      })}
      {running ? (
        <li className="animate-fade">
          <Thinking label="Thinking…" boxed />
        </li>
      ) : null}
    </ol>
  );
}
