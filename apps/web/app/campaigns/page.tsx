"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { listCampaigns } from "@/lib/api";
import type { CampaignSummary } from "@/lib/types";
import { Badge, Card, PageHeader, Skeleton } from "@/components/ui";
import { compact, inr, roasX } from "@/lib/format";

const STATUS_TONE = {
  completed: "green",
  sending: "indigo",
  pending_approval: "amber",
  draft: "slate",
} as const;

export default function CampaignsPage() {
  const { data, isLoading } = useQuery({ queryKey: ["campaigns"], queryFn: listCampaigns });
  return (
    <div>
      <PageHeader title="Campaigns" subtitle="Every play the agent has proposed or run." />
      <div className="p-4 sm:p-6 lg:p-8">
        <Card className="overflow-hidden" hover={false}>
          <div className="overflow-x-auto">
          <table className="w-full min-w-[680px] text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
              <tr className="border-b border-white/[0.07]">
                <th className="px-4 py-3 font-medium">Campaign</th>
                <th className="px-4 py-3 font-medium">Channel</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 text-right font-medium">Audience</th>
                <th className="px-4 py-3 text-right font-medium">Converted</th>
                <th className="px-4 py-3 text-right font-medium">Revenue</th>
                <th className="px-4 py-3 text-right font-medium">ROAS</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <tr key={i} className="border-b border-white/[0.04]">
                    <td className="px-4 py-4">
                      <Skeleton className="h-4 w-44" />
                      <Skeleton className="mt-2 h-3 w-60" />
                    </td>
                    <td className="px-4 py-4"><Skeleton className="h-5 w-20 rounded-full" /></td>
                    <td className="px-4 py-4"><Skeleton className="h-5 w-24 rounded-full" /></td>
                    <td className="px-4 py-4"><Skeleton className="ml-auto h-4 w-12" /></td>
                    <td className="px-4 py-4"><Skeleton className="ml-auto h-4 w-10" /></td>
                    <td className="px-4 py-4"><Skeleton className="ml-auto h-4 w-16" /></td>
                    <td className="px-4 py-4"><Skeleton className="ml-auto h-4 w-10" /></td>
                  </tr>
                ))
              ) : (
                data?.map((c: CampaignSummary, i: number) => (
                  <tr
                    key={c.id}
                    style={{ animationDelay: `${i * 45}ms` }}
                    className="animate-fade-up border-b border-white/[0.04] transition-colors hover:bg-white/[0.03]"
                  >
                    <td className="px-4 py-3">
                      <Link
                        href={`/campaigns/${c.id}`}
                        className="font-medium text-slate-100 hover:text-indigo-300"
                      >
                        {c.name}
                      </Link>
                      <div className="text-xs text-slate-500">
                        {c.goal.length > 54 ? c.goal.slice(0, 54) + "…" : c.goal}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone="slate">{c.channel}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone={STATUS_TONE[c.status]} pulse={c.status === "sending"}>
                        {c.status.replace("_", " ")}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">{compact(c.audience)}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{compact(c.converted)}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{inr(c.revenue)}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{c.roas ? roasX(c.roas) : "—"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
          </div>
        </Card>
      </div>
    </div>
  );
}
