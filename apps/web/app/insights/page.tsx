"use client";

import { useQuery } from "@tanstack/react-query";
import { getCalibration, getChannelRoi, getSummary } from "@/lib/api";
import { Card, PageHeader, Stat } from "@/components/ui";
import { CalibrationChart, ChannelRoiChart } from "@/components/charts";
import { inr, pct, roasX } from "@/lib/format";

function Loading() {
  return <div className="grid h-[260px] place-items-center text-sm text-slate-500">Loading…</div>;
}

const cap = (s: string) => (s ? s[0].toUpperCase() + s.slice(1) : s);

export default function InsightsPage() {
  const roi = useQuery({ queryKey: ["roi"], queryFn: getChannelRoi });
  const cal = useQuery({ queryKey: ["cal"], queryFn: getCalibration });
  const sum = useQuery({ queryKey: ["summary"], queryFn: getSummary });

  const best = roi.data?.[0];
  const convRate =
    sum.data && sum.data.totalSent > 0 ? sum.data.totalConverted / sum.data.totalSent : 0;
  const predErr =
    cal.data && cal.data.length
      ? cal.data.reduce(
          (a, p) => a + Math.abs(p.predictedRoas - p.actualRoas) / (p.predictedRoas || 1),
          0,
        ) / cal.data.length
      : 0;

  return (
    <div>
      <PageHeader
        title="Insights"
        subtitle="Channel ROI and how the agent's predictions track reality over time."
      />
      <div className="space-y-6 p-8">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Card>
            <Stat
              label="Best channel"
              value={best ? cap(best.channel) : "—"}
              sub={best ? `${roasX(best.roas)} ROAS` : "—"}
            />
          </Card>
          <Card>
            <Stat label="Avg convert" value={pct(convRate)} sub="live · all campaigns" />
          </Card>
          <Card>
            <Stat label="Revenue" value={inr(sum.data?.totalRevenue ?? 0)} sub="attributed" />
          </Card>
          <Card>
            <Stat
              label="Prediction error"
              value={`${Math.round(predErr * 100)}%`}
              sub="predicted vs actual ROAS"
            />
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="p-4">
            <div className="mb-2 text-sm font-medium text-slate-200">ROAS by channel</div>
            {roi.data ? <ChannelRoiChart data={roi.data} /> : <Loading />}
          </Card>
          <Card className="p-4">
            <div className="text-sm font-medium text-slate-200">Predicted vs actual ROAS</div>
            <div className="mb-2 text-xs text-slate-400">
              The gap narrows as the agent learns from each campaign.
            </div>
            {cal.data ? <CalibrationChart points={cal.data} /> : <Loading />}
          </Card>
        </div>
      </div>
    </div>
  );
}
