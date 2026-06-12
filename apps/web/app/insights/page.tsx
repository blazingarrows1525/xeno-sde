"use client";

import { useQuery } from "@tanstack/react-query";
import { Gauge, ArrowUpRight, Activity, Megaphone, BarChart3 } from "lucide-react";
import { getCalibration, getChannelRoi, getSummary } from "@/lib/api";
import { Card, ChartSkeleton, PageHeader, Stat } from "@/components/ui";
import { CalibrationChart, ChannelRoiChart } from "@/components/charts";
import { CountUp } from "@/components/count-up";
import { AccuracyRing } from "@/components/accuracy-ring";
import { inr, roasX } from "@/lib/format";

const Loading = () => <ChartSkeleton />;

const cap = (s: string) => (s ? s[0].toUpperCase() + s.slice(1) : s);
const errOf = (p: { predictedRoas: number; actualRoas: number }) =>
  Math.abs(p.predictedRoas - p.actualRoas) / (p.predictedRoas || 1);

export default function InsightsPage() {
  const roi = useQuery({ queryKey: ["roi"], queryFn: getChannelRoi });
  const cal = useQuery({ queryKey: ["cal"], queryFn: getCalibration });
  const sum = useQuery({ queryKey: ["summary"], queryFn: getSummary });

  const best = roi.data?.[0];
  const convRate =
    sum.data && sum.data.totalSent > 0 ? sum.data.totalConverted / sum.data.totalSent : 0;

  const cd = cal.data ?? [];
  const accuracyNow = cd.length ? (1 - errOf(cd[cd.length - 1])) * 100 : 0;
  const accuracyFirst = cd.length ? (1 - errOf(cd[0])) * 100 : 0;
  const improvement = accuracyNow - accuracyFirst;

  return (
    <div>
      <PageHeader
        title="Insights"
        subtitle="Channel ROI and how the agent's predictions track reality over time."
      />
      <div className="space-y-5 p-4 sm:p-6 lg:space-y-6 lg:p-8">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Card delay={0}>
            <Stat
              icon={<Megaphone size={15} />}
              label="Best channel"
              value={best ? cap(best.channel) : "—"}
              sub={best ? `${roasX(best.roas)} ROAS` : "—"}
            />
          </Card>
          <Card delay={60}>
            <Stat
              icon={<Activity size={15} />}
              label="Avg convert"
              to={convRate * 100}
              format={(n) => `${n.toFixed(1)}%`}
              sub="live · all campaigns"
            />
          </Card>
          <Card delay={120}>
            <Stat
              icon={<ArrowUpRight size={15} />}
              label="Revenue"
              to={sum.data?.totalRevenue ?? 0}
              format={inr}
              sub="attributed"
            />
          </Card>
          <Card delay={180}>
            <Stat
              icon={<BarChart3 size={15} />}
              label="Campaigns run"
              to={sum.data?.totalCampaigns ?? 0}
              format={(n) => Math.round(n).toString()}
              sub="proposed & launched"
            />
          </Card>
        </div>

        {/* Learning hero — the agent's forecasts converging on reality */}
        <Card className="relative overflow-hidden p-5" delay={60}>
          <div className="pointer-events-none absolute -right-12 -top-12 h-48 w-48 rounded-full bg-emerald-500/10 blur-3xl" />
          <div className="relative flex items-center justify-between gap-6">
            <div>
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-emerald-300">
                <Gauge size={14} /> The agent is learning
              </div>
              <div className="mt-2 flex items-end gap-3">
                <div className="text-4xl font-semibold text-slate-100 tabular-nums">
                  <CountUp to={accuracyNow} duration={1300} format={(n) => `${n.toFixed(0)}%`} />
                </div>
                {improvement > 0.5 ? (
                  <div className="mb-1.5 inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs font-medium text-emerald-300">
                    <ArrowUpRight size={13} /> +{improvement.toFixed(0)} pp
                  </div>
                ) : null}
              </div>
              <p className="mt-1.5 max-w-md text-sm text-slate-400">
                Forecast accuracy, up from{" "}
                <span className="text-slate-300">{accuracyFirst.toFixed(0)}%</span> on the first
                campaign. Each send teaches the agent — predictions converge on reality.
              </p>
            </div>
            <div className="hidden shrink-0 sm:block">
              <AccuracyRing value={accuracyNow} />
            </div>
          </div>
        </Card>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="p-4" delay={80}>
            <div className="mb-2 text-sm font-medium text-slate-200">ROAS by channel</div>
            {roi.data ? <ChannelRoiChart data={roi.data} /> : <Loading />}
          </Card>
          <Card className="p-4" delay={140}>
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
