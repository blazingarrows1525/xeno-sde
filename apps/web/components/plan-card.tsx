"use client";

import { Check } from "lucide-react";
import type { AgentPlan } from "@/lib/types";
import { compact, inr, pct, roasX } from "@/lib/format";
import { Badge, Button, Tip } from "./ui";

export function PlanCard({
  plan,
  approved,
  onApprove,
}: {
  plan: AgentPlan;
  approved: boolean;
  onApprove: () => void;
}) {
  const p = plan.predicted;
  const kpis: [string, string][] = [
    ["Audience", compact(p.audience)],
    ["Predicted convert", pct(p.convertRate)],
    ["Predicted revenue", inr(p.revenue)],
    ["Predicted ROAS", roasX(p.roas)],
  ];
  return (
    <div className="animate-scale-in rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-5">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs uppercase tracking-wide text-emerald-300">Proposed campaign</div>
          <h3 className="mt-1 text-lg font-semibold text-slate-100">{plan.segmentName}</h3>
        </div>
        <Badge tone="indigo">{plan.channel}</Badge>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {kpis.map(([k, v]) => (
          <div key={k} className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
            <div className="text-xs text-slate-400">{k}</div>
            <div className="mt-0.5 text-lg font-semibold text-slate-100">{v}</div>
          </div>
        ))}
      </div>

      <div className="mt-4 space-y-2">
        {plan.variants.map((v) => (
          <div key={v.label} className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
            <div className="text-xs font-semibold text-slate-400">Variant {v.label}</div>
            <div className="mt-1 text-sm text-slate-200">{v.body}</div>
          </div>
        ))}
      </div>

      <p className="mt-3 text-xs text-slate-400">{plan.rationale}</p>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Tip tip="Passes the human-approval gate: creates this campaign, sends it to the matched audience, and completes with a real delivery funnel and ROAS.">
          <Button onClick={onApprove} disabled={approved}>
            <Check size={16} className="icon-pop" />{" "}
            {approved ? "Approved & launched" : "Approve & launch"}
          </Button>
        </Tip>
        {approved ? (
          <Badge tone="green">sending through channel service</Badge>
        ) : (
          <span className="text-xs text-slate-500">
            You stay in control — nothing sends until you approve.
          </span>
        )}
      </div>
    </div>
  );
}
