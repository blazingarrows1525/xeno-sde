"use client";

import { useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import { runAgent } from "@/lib/api";
import type { AgentPlan, AgentStep } from "@/lib/types";
import { Card, PageHeader } from "@/components/ui";
import { ReasoningTrace } from "@/components/reasoning-trace";
import { PlanCard } from "@/components/plan-card";

const STARTERS = [
  "Bring back customers who haven't ordered in 60 days and maximize ROI",
  "Reward my top 10% spenders with an exclusive offer",
  "Convert one-time buyers into repeat customers",
];

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export default function ConsolePage() {
  const [goal, setGoal] = useState(STARTERS[0]);
  const [running, setRunning] = useState(false);
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [plan, setPlan] = useState<AgentPlan | null>(null);
  const [approved, setApproved] = useState(false);

  async function run() {
    if (running) return;
    setRunning(true);
    setSteps([]);
    setPlan(null);
    setApproved(false);
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
