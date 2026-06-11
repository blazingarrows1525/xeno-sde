"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getCampaign } from "@/lib/api";
import type { EventType } from "@/lib/types";
import { Badge, Card, PageHeader, Stat } from "@/components/ui";
import { FunnelChart } from "@/components/charts";
import { compact, inr, pct, roasX } from "@/lib/format";

const STATE_TONE: Record<EventType, "green" | "indigo" | "slate" | "red"> = {
  converted: "green",
  clicked: "indigo",
  read: "slate",
  opened: "slate",
  delivered: "slate",
  sent: "slate",
  failed: "red",
};

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-slate-400">{label}</span>
      <span className="font-medium text-slate-200">{value}</span>
    </div>
  );
}

export default function CampaignDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const { data: c, isLoading } = useQuery({
    queryKey: ["campaign", id],
    queryFn: () => getCampaign(id),
    enabled: Boolean(id),
  });

  if (isLoading || !c) return <div className="p-4 text-slate-500 sm:p-6 lg:p-8">Loading…</div>;
  const f = c.funnel;

  return (
    <div>
      <PageHeader title={c.name} subtitle={c.goal} actions={<Badge tone="indigo">{c.channel}</Badge>} />
      <div className="space-y-5 p-4 sm:p-6 lg:space-y-6 lg:p-8">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Card>
            <Stat label="Delivered" value={pct(f.delivered / f.sent)} sub={`${compact(f.delivered)} of ${compact(f.sent)}`} />
          </Card>
          <Card>
            <Stat label="Clicked" value={pct(f.clicked / f.sent)} sub={`${compact(f.clicked)} clicks`} />
          </Card>
          <Card>
            <Stat label="Converted" value={compact(f.converted)} sub={`${pct(f.converted / f.sent)} of sent`} />
          </Card>
          <Card>
            <Stat label="Revenue / ROAS" value={inr(c.revenue)} sub={`${roasX(c.roas)} return`} />
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="p-4">
            <div className="mb-2 text-sm font-medium text-slate-200">Delivery funnel</div>
            <FunnelChart funnel={f} />
          </Card>
          <Card className="p-4">
            <div className="mb-3 text-sm font-medium text-slate-200">Predicted vs actual</div>
            <div className="space-y-2 text-sm">
              <Row label="Predicted ROAS" value={roasX(c.predicted.roas)} />
              <Row label="Actual ROAS" value={roasX(c.roas)} />
              <Row label="Predicted convert" value={pct(c.predicted.convertRate)} />
              <Row label="Actual convert" value={pct(f.converted / f.sent)} />
            </div>
            <div className="mb-2 mt-4 text-sm font-medium text-slate-200">Variants</div>
            <div className="space-y-2">
              {c.variants.map((v) => (
                <div
                  key={v.variant}
                  className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2 text-sm"
                >
                  <span>Variant {v.variant}</span>
                  <span className="text-slate-400">
                    {compact(v.clicked)} clicks · {compact(v.converted)} conv
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <Card className="p-4">
          <div className="mb-3 text-sm font-medium text-slate-200">Recent message events</div>
          <div className="space-y-1">
            {c.timeline.map((t, i) => (
              <div
                key={i}
                className="flex items-center justify-between gap-3 rounded-lg px-3 py-2 text-sm hover:bg-slate-800/30"
              >
                <span className="min-w-0 truncate text-slate-200">{t.customer}</span>
                <span className="flex shrink-0 items-center gap-2 sm:gap-3">
                  <span className="hidden text-xs text-slate-500 sm:inline">var {t.variant}</span>
                  <Badge tone={STATE_TONE[t.state]}>{t.state}</Badge>
                  <span className="text-xs text-slate-500">{t.at}</span>
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
