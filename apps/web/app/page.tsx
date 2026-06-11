"use client";

import { useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import {
  runAgent,
  streamAgent,
  isLiveBackend,
  type AgentStreamEvent,
} from "@/lib/api";
import type { AgentPlan, AgentStep } from "@/lib/types";
import { Badge, Card, PageHeader } from "@/components/ui";
import { ReasoningTrace } from "@/components/reasoning-trace";
import { PlanCard } from "@/components/plan-card";
import { AgentPlanText } from "@/components/agent-plan-text";

const STARTERS = [
  "Bring back customers who haven't ordered in 60 days and maximize ROI",
  "Reward my top 10% spenders with an exclusive offer",
  "Convert one-time buyers into repeat customers",
];

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

// Map a live SSE event into the trace item the UI renders.
function liveStepToAgentStep(ev: AgentStreamEvent): AgentStep | null {
  if (ev.kind === "tool_call") {
    const dsl = (ev.tool_input?.dsl ?? null) as {
      rules?: { field: string; op: string; value?: unknown }[];
      match?: string;
    } | null;
    let detail: string | undefined = ev.tool ? `calling ${ev.tool}` : undefined;
    if (dsl?.rules?.length) {
      const join = dsl.match === "any" ? "  OR  " : "  AND  ";
      detail = dsl.rules
        .map((r) => `${r.field} ${r.op}${r.value !== undefined ? " " + String(r.value) : ""}`)
        .join(join);
    }
    return { kind: "tool_call", title: ev.tool ?? "tool", detail, tool: ev.tool };
  }
  if (ev.kind === "tool_result") {
    const out = ev.tool_output ?? {};
    if (typeof out.estimated_size === "number") {
      return {
        kind: "tool_result",
        title: `${out.estimated_size.toLocaleString()} customers match`,
        detail: "compiled to parameterized SQL · injection-safe",
      };
    }
    if (typeof out.error === "string") {
      return {
        kind: "tool_result",
        title: "validation rejected by the typed DSL",
        detail: out.error.split("\n")[0].slice(0, 120),
      };
    }
    return { kind: "tool_result", title: "result", detail: undefined };
  }
  if (ev.kind === "awaiting_approval") {
    return {
      kind: "plan",
      title: "Awaiting your approval",
      detail: `${ev.tool ?? "action"} is gated until you approve`,
    };
  }
  if (ev.kind === "error") {
    return {
      kind: "tool_result",
      title: "error",
      detail: typeof ev.tool_output?.error === "string" ? ev.tool_output.error : undefined,
    };
  }
  if (ev.kind === "final") {
    return { kind: "final", title: "Plan ready", detail: "proposed for your approval" };
  }
  return null;
}

export default function ConsolePage() {
  const [goal, setGoal] = useState(STARTERS[0]);
  const [running, setRunning] = useState(false);
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [plan, setPlan] = useState<AgentPlan | null>(null);
  const [planText, setPlanText] = useState<string | null>(null);
  const [approved, setApproved] = useState(false);

  async function run() {
    if (running) return;
    setRunning(true);
    setSteps([]);
    setPlan(null);
    setPlanText(null);
    setApproved(false);

    if (isLiveBackend) {
      try {
        await streamAgent(goal, (ev) => {
          if (ev.type === "complete") return;
          if (ev.kind === "final") setPlanText(String(ev.tool_output?.text ?? ""));
          const step = liveStepToAgentStep(ev);
          if (step) setSteps((prev) => [...prev, step]);
        });
      } catch (e) {
        setSteps((prev) => [
          ...prev,
          { kind: "tool_result", title: "stream error", detail: String(e) },
        ]);
      }
      setRunning(false);
      return;
    }

    // Mock fallback (NEXT_PUBLIC_API_URL unset)
    const result = runAgent(goal);
    for (const step of result.steps) {
      await sleep(520);
      setSteps((prev) => [...prev, step]);
    }
    setPlan(result.plan);
    setRunning(false);
  }

  return (
    <div>
      <PageHeader
        title="Agent Console"
        subtitle="State a goal. Kairos reasons, proposes a campaign with predicted ROI, and waits for your approval."
        actions={
          isLiveBackend ? (
            <Badge tone="green">live · Claude</Badge>
          ) : (
            <Badge tone="slate">demo data</Badge>
          )
        }
      />
      <div className="grid gap-6 p-8 lg:grid-cols-2">
        <div className="space-y-4">
          <Card className="p-4">
            <label className="text-xs uppercase tracking-wide text-slate-400">Marketing goal</label>
            <textarea
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              rows={3}
              className="mt-2 w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-indigo-500"
            />
            <div className="mt-3 flex flex-wrap gap-2">
              {STARTERS.map((s) => (
                <button
                  key={s}
                  onClick={() => setGoal(s)}
                  className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 transition hover:border-indigo-500"
                >
                  {s.length > 42 ? s.slice(0, 42) + "…" : s}
                </button>
              ))}
            </div>
            <button
              onClick={run}
              disabled={running}
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-400 disabled:opacity-60"
            >
              {running ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
              {running ? "Reasoning…" : "Run agent"}
            </button>
          </Card>

          {plan ? <PlanCard plan={plan} approved={approved} onApprove={() => setApproved(true)} /> : null}

          {planText ? (
            <Card className="p-4">
              <div className="mb-2 flex items-center justify-between">
                <div className="text-xs uppercase tracking-wide text-slate-400">Proposed plan</div>
                {approved ? (
                  <Badge tone="green">approved</Badge>
                ) : (
                  <Badge tone="amber">awaiting approval</Badge>
                )}
              </div>
              <AgentPlanText text={planText} />
              <button
                onClick={() => setApproved(true)}
                disabled={approved || running}
                className="mt-4 w-full rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-400 disabled:opacity-60"
              >
                {approved ? "Approved — ready to launch" : "Approve & launch"}
              </button>
            </Card>
          ) : null}
        </div>

        <Card className="p-4">
          <div className="mb-3 text-xs uppercase tracking-wide text-slate-400">
            Reasoning trace · glass box
          </div>
          <ReasoningTrace steps={steps} />
        </Card>
      </div>
    </div>
  );
}
