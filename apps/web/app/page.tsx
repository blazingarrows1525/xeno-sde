"use client";

import { useState } from "react";
import { Check, Sparkles } from "lucide-react";
import {
  runAgent,
  streamAgent,
  launchCampaign,
  inferChannel,
  isLiveBackend,
  type AgentStreamEvent,
} from "@/lib/api";
import type { AgentPlan, AgentStep } from "@/lib/types";
import { Badge, Button, Card, PageHeader, Tip } from "@/components/ui";
import { ReasoningTrace } from "@/components/reasoning-trace";
import { PlanCard } from "@/components/plan-card";
import { AgentPlanText } from "@/components/agent-plan-text";

// Each starter carries a gist of the play the agent will propose for it —
// surfaced as a hover tooltip so you know the answer before you ask.
const STARTERS: { goal: string; gist: string }[] = [
  {
    goal: "Bring back customers who haven't ordered in 60 days and maximize ROI",
    gist: "Builds a win-back segment of 60-day-dormant shoppers, picks the highest-ROI channel, and drafts two message variants with a predicted ROAS.",
  },
  {
    goal: "Reward my top 10% spenders with an exclusive offer",
    gist: "Finds your highest-LTV decile and proposes a VIP exclusive with A/B variants and a revenue forecast.",
  },
  {
    goal: "Convert one-time buyers into repeat customers",
    gist: "Segments single-order customers and plans a second-purchase nudge with predicted conversion uplift.",
  },
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
  const [goal, setGoal] = useState(STARTERS[0].goal);
  const [running, setRunning] = useState(false);
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [plan, setPlan] = useState<AgentPlan | null>(null);
  const [planText, setPlanText] = useState<string | null>(null);
  const [approved, setApproved] = useState(false);
  const [launching, setLaunching] = useState(false);
  const [launched, setLaunched] = useState<{ id: string; name: string } | null>(null);
  const [audience, setAudience] = useState(0);

  async function run() {
    if (running) return;
    setRunning(true);
    setSteps([]);
    setPlan(null);
    setPlanText(null);
    setApproved(false);
    setLaunching(false);
    setLaunched(null);
    setAudience(0);

    if (isLiveBackend) {
      try {
        await streamAgent(goal, (ev) => {
          if (ev.type === "complete") return;
          if (ev.kind === "final") setPlanText(String(ev.tool_output?.text ?? ""));
          if (
            ev.kind === "tool_result" &&
            typeof ev.tool_output?.estimated_size === "number"
          ) {
            setAudience(ev.tool_output.estimated_size as number);
          }
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

  async function approve() {
    if (approved || launching || launched) return;
    setApproved(true);
    setLaunching(true);
    setSteps((prev) => [
      ...prev,
      {
        kind: "tool_call",
        title: "Approval granted",
        detail: "creating the campaign and passing the approval gate",
      },
    ]);
    try {
      const channel = inferChannel(planText ?? goal);
      const res = await launchCampaign({ goal, channel, audience });
      setLaunched({ id: res.id, name: res.name });
      setSteps((prev) => [
        ...prev,
        {
          kind: "final",
          title: "Campaign launched",
          detail: `“${res.name}” is now sending via ${channel}`,
        },
      ]);
    } catch (e) {
      setApproved(false);
      setSteps((prev) => [
        ...prev,
        { kind: "tool_result", title: "launch failed", detail: String(e) },
      ]);
    } finally {
      setLaunching(false);
    }
  }

  return (
    <div>
      <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-20 left-1/4 h-80 w-80 rounded-full bg-emerald-600/10 blur-3xl animate-float" />
        <div
          className="absolute bottom-10 right-1/4 h-80 w-80 rounded-full bg-sky-500/10 blur-3xl animate-float"
          style={{ animationDelay: "2.5s" }}
        />
      </div>
      <PageHeader
        title="Agent Console"
        subtitle="State a goal. Kairos reasons, proposes a campaign with predicted ROI, and waits for your approval."
      />
      <div className="grid gap-5 p-4 sm:p-6 lg:grid-cols-2 lg:gap-6 lg:p-8">
        <div className="space-y-4">
          <Card className="p-5" delay={60}>
            <label className="text-xs font-medium uppercase tracking-wide text-slate-400">
              Marketing goal
            </label>
            <textarea
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              rows={3}
              placeholder="Describe what you want to achieve…"
              className="mt-2 w-full resize-none rounded-xl border border-white/[0.08] bg-zinc-950/60 px-3.5 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-emerald-500/60 focus:ring-4 focus:ring-emerald-500/10"
            />
            <div className="mt-3 flex flex-wrap gap-2">
              {STARTERS.map((s) => (
                <Tip
                  key={s.goal}
                  tip={
                    <>
                      <span className="block font-medium text-slate-200">{s.goal}</span>
                      <span className="mt-1 block text-slate-400">{s.gist}</span>
                    </>
                  }
                >
                  <button
                    onClick={() => setGoal(s.goal)}
                    className="btn-tactile rounded-full border border-white/[0.08] bg-white/[0.02] px-3 py-1 text-xs text-slate-300 hover:border-emerald-500/50 hover:bg-emerald-500/10 hover:text-emerald-200"
                  >
                    {s.goal.length > 42 ? s.goal.slice(0, 42) + "…" : s.goal}
                  </button>
                </Tip>
              ))}
            </div>
            <Tip
              className="mt-4"
              tip="Streams the agent's reasoning live — segment queries, audience sizing, and a proposed campaign with predicted ROI. Nothing sends without your approval."
            >
              <Button onClick={run} loading={running}>
                {running ? (
                  "Reasoning…"
                ) : (
                  <>
                    <Sparkles size={16} className="icon-pop" /> Run agent
                  </>
                )}
              </Button>
            </Tip>
          </Card>

          {plan ? <PlanCard plan={plan} approved={approved} onApprove={approve} /> : null}

          {planText ? (
            <Card className="p-4">
              <div className="mb-2 flex items-center justify-between">
                <div className="text-xs uppercase tracking-wide text-slate-400">Proposed plan</div>
                {launched ? (
                  <Badge tone="green">launched · sending</Badge>
                ) : launching ? (
                  <Badge tone="amber">launching…</Badge>
                ) : approved ? (
                  <Badge tone="green">approved</Badge>
                ) : (
                  <Badge tone="amber">awaiting approval</Badge>
                )}
              </div>
              <AgentPlanText text={planText} />
              {launched ? (
                <Tip
                  className="mt-4 w-full"
                  tip="Opens Campaigns to see this run live — delivery funnel, conversions, and ROAS."
                >
                  <a
                    href="/campaigns"
                    className="btn-tactile flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-500/15 px-4 py-2.5 text-sm font-medium text-emerald-300 hover:bg-emerald-500/25"
                  >
                    <Check size={16} className="icon-pop" /> Launched — view in Campaigns
                  </a>
                </Tip>
              ) : (
                <Tip
                  className="mt-4 w-full"
                  tip="Passes the human-approval gate: creates this campaign, sends it to the matched audience, and completes with a real delivery funnel and ROAS."
                >
                  <Button onClick={approve} disabled={running} loading={launching} fullWidth>
                    {launching ? "Launching…" : "Approve & launch"}
                  </Button>
                </Tip>
              )}
            </Card>
          ) : null}
        </div>

        <Card className="p-4" delay={140}>
          <div className="mb-3 flex items-center gap-2 text-xs uppercase tracking-wide text-slate-400">
            Reasoning trace · glass box
            {running ? <span className="live-dot" /> : null}
          </div>
          <ReasoningTrace steps={steps} running={running} />
        </Card>
      </div>
    </div>
  );
}
