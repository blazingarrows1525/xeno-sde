"use client";

import { useQuery } from "@tanstack/react-query";
import { getCalibration, getChannelRoi } from "@/lib/api";
import { Card, PageHeader, Stat } from "@/components/ui";
import { CalibrationChart, ChannelRoiChart } from "@/components/charts";
import { inr, pct } from "@/lib/format";

function Loading() {
  return <div className="grid h-[260px] place-items-center text-sm text-slate-500">Loading…</div>;
}

export default function InsightsPage() {
  const roi = useQuery({ queryKey: ["roi"], queryFn: getChannelRoi });
  const cal = useQuery({ queryKey: ["cal"], queryFn: getCalibration });

  return (
    <div>
      <PageHeader
        title="Insights"
        subtitle="Channel ROI and how the agent's predictions track reality over time."
      />
      <div className="space-y-6 p-8">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Card>
            <Stat label="Best channel" value="WhatsApp" sub="6.8× ROAS" />
          </Card>
          <Card>
            <Stat label="Avg convert" value={pct(0.041)} sub="across campaigns" />
          </Card>
          <Card>
            <Stat label="Revenue (30d)" value={inr(958300)} sub="attributed" />
          </Card>
          <Card>
            <Stat label="Prediction error" value="6%" sub="predicted vs actual ROAS" />
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
