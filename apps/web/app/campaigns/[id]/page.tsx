"use client";

import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ShieldCheck, Sparkles } from "lucide-react";
import { approveCampaign, getCampaign } from "@/lib/api";
import type { EventType } from "@/lib/types";
import { Badge, Button, Card, PageHeader, Skeleton, Stat } from "@/components/ui";
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
  const queryClient = useQueryClient();
  const { data: c, isLoading } = useQuery({
    queryKey: ["campaign", id],
    queryFn: () => getCampaign(id),
    enabled: Boolean(id),
  });

  const approve = useMutation({
    mutationFn: () => approveCampaign(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaign", id] });
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      queryClient.invalidateQueries({ queryKey: ["summary"] });
      queryClient.invalidateQueries({ queryKey: ["roi"] });
      queryClient.invalidateQueries({ queryKey: ["cal"] });
    },
  });

  if (isLoading || !c)
    return (
      <div>
        <div className="border-b border-white/[0.06] px-4 py-5 sm:px-6 lg:px-8 lg:py-6">
          <Skeleton className="h-7 w-64 max-w-full" />
          <Skeleton className="mt-2.5 h-4 w-96 max-w-full" />
        </div>
        <div className="space-y-5 p-4 sm:p-6 lg:space-y-6 lg:p-8">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-28 rounded-2xl" />
            ))}
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <Skeleton className="h-80 rounded-2xl" />
            <Skeleton className="h-80 rounded-2xl" />
          </div>
        </div>
      </div>
    );
  const f = c.funnel;
  // Campaigns that haven't sent yet have an all-zero funnel — never show NaN%.
  const rate = (n: number) => (f.sent ? pct(n / f.sent) : "—");
  const awaitingApproval = c.status === "pending_approval" || c.status === "draft";

  return (
    <div>
      <PageHeader title={c.name} subtitle={c.goal} actions={<Badge tone="indigo">{c.channel}</Badge>} />
      <div className="space-y-5 p-4 sm:p-6 lg:space-y-6 lg:p-8">
        {awaitingApproval ? (
          <div className="animate-scale-in flex flex-col gap-3 rounded-2xl border border-amber-500/25 bg-gradient-to-r from-amber-500/[0.08] to-transparent p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-amber-500/15 text-amber-300">
                <ShieldCheck size={18} />
              </span>
              <div>
                <div className="text-sm font-semibold text-slate-100">Awaiting your approval</div>
                <p className="mt-0.5 text-xs text-slate-400">
                  The agent proposed this campaign and is holding it. Nothing sends until you sign off.
                </p>
              </div>
            </div>
            <Button
              onClick={() => approve.mutate()}
              loading={approve.isPending}
              className="shrink-0"
            >
              {approve.isPending ? (
                "Launching…"
              ) : (
                <>
                  <Sparkles size={16} className="icon-pop" /> Approve &amp; launch
                </>
              )}
            </Button>
          </div>
        ) : null}
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Card delay={0}>
            <Stat label="Delivered" value={rate(f.delivered)} sub={`${compact(f.delivered)} of ${compact(f.sent)}`} />
          </Card>
          <Card delay={60}>
            <Stat label="Clicked" value={rate(f.clicked)} sub={`${compact(f.clicked)} clicks`} />
          </Card>
          <Card delay={120}>
            <Stat label="Converted" value={compact(f.converted)} sub={f.sent ? `${pct(f.converted / f.sent)} of sent` : "no sends yet"} />
          </Card>
          <Card delay={180}>
            <Stat label="Revenue / ROAS" value={inr(c.revenue)} sub={c.roas ? `${roasX(c.roas)} return` : "awaiting results"} />
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
              <Row label="Actual convert" value={rate(f.converted)} />
            </div>
            <div className="mb-2 mt-4 text-sm font-medium text-slate-200">Variants</div>
            <div className="space-y-2">
              {c.variants.map((v) => (
                <div
                  key={v.variant}
                  className="flex items-center justify-between rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-sm"
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
          {c.timeline.length === 0 ? (
            <div className="rounded-xl border border-dashed border-white/[0.08] px-4 py-8 text-center text-sm text-slate-500">
              No message events yet — they appear here as the campaign sends.
            </div>
          ) : null}
          <div className="space-y-1">
            {c.timeline.map((t, i) => (
              <div
                key={i}
                className="flex items-center justify-between gap-3 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-white/[0.03]"
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
