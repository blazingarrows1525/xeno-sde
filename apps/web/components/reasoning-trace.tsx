import { Brain, CheckCircle2, FileText, Sparkles, Wrench } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { AgentStep } from "@/lib/types";

const META: Record<AgentStep["kind"], { icon: LucideIcon; tone: string }> = {
  thought: { icon: Brain, tone: "text-sky-300" },
  tool_call: { icon: Wrench, tone: "text-indigo-300" },
  tool_result: { icon: CheckCircle2, tone: "text-emerald-300" },
  plan: { icon: FileText, tone: "text-amber-300" },
  final: { icon: Sparkles, tone: "text-violet-300" },
};

export function ReasoningTrace({ steps }: { steps: AgentStep[] }) {
  if (steps.length === 0) {
    return (
      <p className="text-sm text-slate-500">{"The agent's reasoning will stream here, step by step."}</p>
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
            className="flex gap-3 rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2"
          >
            <Icon size={16} className={`mt-0.5 shrink-0 ${meta.tone}`} />
            <div className="min-w-0">
              <div className="text-sm">
                {step.tool ? (
                  <span className="font-mono text-xs text-indigo-300">{step.tool}</span>
                ) : (
                  <span className="font-medium text-slate-200">{step.title}</span>
                )}
                {step.tool ? <span className="ml-2 text-slate-300">{step.title}</span> : null}
              </div>
              {step.detail ? <div className="mt-0.5 text-xs text-slate-400">{step.detail}</div> : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
