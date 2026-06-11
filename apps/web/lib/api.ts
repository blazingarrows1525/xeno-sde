import {
  buildAgentRun,
  MOCK_CALIBRATION,
  MOCK_CAMPAIGNS,
  MOCK_CHANNEL_ROI,
  mockCampaignDetail,
} from "./mock";
import type {
  CalibrationPoint,
  CampaignDetail,
  CampaignSummary,
  Channel,
  ChannelRoi,
  EventType,
  FunnelStat,
} from "./types";

// When NEXT_PUBLIC_API_URL is set, these resolve real fetch() calls against the CRM service;
// otherwise they fall back to mock data so the UI is demoable without a backend.
const BASE = process.env.NEXT_PUBLIC_API_URL;

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return (await res.json()) as T;
}

// ── backend response shapes ────────────────────────────────────────────────
interface ApiStats {
  sent: number; delivered: number; failed: number; opened: number;
  read: number; clicked: number; converted: number; revenue: number; send_cost: number;
}
interface ApiCampaign {
  id: string; name: string; channel: string; status: string; goal_text: string | null;
  predicted_kpis?: Record<string, number> | null; created_at: string; stats?: ApiStats | null;
}
interface ApiCampaignDetail extends ApiCampaign {
  funnel?: Partial<FunnelStat> | null;
  timeline?: { state: string; at: string; variant: string; customer: string }[];
  variants?: { variant: string; total: number; clicked: number; converted: number }[];
}
interface ApiChannelRoi {
  channel: string; revenue: number; cost: number; roas: number;
  campaigns: number; sent: number; delivered?: number; converted: number;
}
interface ApiCalibration { campaign: string; predicted: number; actual: number }

// ── mappers ────────────────────────────────────────────────────────────────
function mapStatus(s: string): CampaignSummary["status"] {
  if (s === "completed" || s === "sending" || s === "pending_approval" || s === "draft") return s;
  if (s === "approved") return "sending";
  return "draft";
}

function fmtTime(iso?: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function toSummary(c: ApiCampaign): CampaignSummary {
  const s = c.stats;
  const revenue = s?.revenue ?? 0;
  const sendCost = s?.send_cost ?? 0;
  return {
    id: c.id,
    name: c.name,
    goal: c.goal_text ?? "",
    channel: (c.channel ?? "whatsapp") as Channel,
    status: mapStatus(c.status),
    audience: c.predicted_kpis?.audience ?? s?.sent ?? 0,
    sent: s?.sent ?? 0,
    converted: s?.converted ?? 0,
    revenue,
    roas: sendCost > 0 ? Math.round((revenue / sendCost) * 10) / 10 : 0,
    createdAt: (c.created_at ?? "").slice(0, 10),
  };
}

function toDetail(c: ApiCampaignDetail): CampaignDetail {
  const f = c.funnel ?? {};
  const p = c.predicted_kpis ?? {};
  return {
    ...toSummary(c),
    funnel: {
      sent: f.sent ?? 0, delivered: f.delivered ?? 0, opened: f.opened ?? 0,
      read: f.read ?? 0, clicked: f.clicked ?? 0, converted: f.converted ?? 0, failed: f.failed ?? 0,
    },
    predicted: {
      audience: p.audience ?? 0,
      deliveredRate: p.deliveredRate ?? 0,
      openRate: p.openRate ?? 0,
      clickRate: p.clickRate ?? 0,
      convertRate: p.convertRate ?? 0,
      revenue: p.revenue ?? 0,
      roas: p.roas ?? 0,
    },
    variants: (c.variants ?? []).map((v) => ({
      variant: (v.variant === "B" ? "B" : "A") as "A" | "B",
      sent: v.total ?? 0,
      clicked: v.clicked ?? 0,
      converted: v.converted ?? 0,
    })),
    timeline: (c.timeline ?? []).map((t) => ({
      customer: t.customer ?? "—",
      variant: (t.variant === "B" ? "B" : "A") as "A" | "B",
      state: t.state as EventType,
      at: fmtTime(t.at),
    })),
  };
}

function shortLabel(name: string): string {
  const head = name.split("·")[0].trim() || name;
  return head.length > 16 ? head.slice(0, 15) + "…" : head;
}

// ── public API ─────────────────────────────────────────────────────────────
export async function listCampaigns(): Promise<CampaignSummary[]> {
  if (!BASE) { await delay(120); return MOCK_CAMPAIGNS; }
  return (await getJSON<ApiCampaign[]>("/v1/campaigns")).map(toSummary);
}

export async function getCampaign(id: string): Promise<CampaignDetail> {
  if (!BASE) { await delay(120); return mockCampaignDetail(id); }
  return toDetail(await getJSON<ApiCampaignDetail>(`/v1/campaigns/${id}`));
}

export async function getChannelRoi(): Promise<ChannelRoi[]> {
  if (!BASE) { await delay(120); return MOCK_CHANNEL_ROI; }
  const rows = await getJSON<ApiChannelRoi[]>("/v1/analytics/channel-roi");
  return rows
    .map((r): ChannelRoi => {
      const delivered = r.delivered ?? Math.round(r.sent * 0.93);
      return {
        channel: (r.channel ?? "whatsapp") as Channel,
        deliverability: r.sent > 0 ? delivered / r.sent : 0,
        convertRate: r.sent > 0 ? r.converted / r.sent : 0,
        cpa: r.converted > 0 ? r.cost / r.converted : 0,
        roas: r.roas ?? 0,
      };
    })
    .sort((a, b) => b.roas - a.roas);
}

export async function getCalibration(): Promise<CalibrationPoint[]> {
  if (!BASE) { await delay(120); return MOCK_CALIBRATION; }
  return (await getJSON<ApiCalibration[]>("/v1/analytics/calibration")).map((p) => ({
    campaign: shortLabel(p.campaign ?? ""),
    predictedRoas: p.predicted ?? 0,
    actualRoas: p.actual ?? 0,
  }));
}

export function runAgent(goal: string) {
  // Mock fallback used when NEXT_PUBLIC_API_URL is unset.
  return buildAgentRun(goal);
}

// A single Server-Sent Event from the live /v1/agent/run stream.
export interface AgentStreamEvent {
  kind?: "tool_call" | "tool_result" | "final" | "awaiting_approval" | "error";
  step_no?: number;
  tool?: string;
  tool_input?: Record<string, unknown>;
  tool_output?: Record<string, unknown>;
  type?: "complete";
  status?: string;
  steps_taken?: number;
}

// POST the goal and stream the agent's reasoning back as it happens (real glass box).
export async function streamAgent(
  goal: string,
  onEvent: (ev: AgentStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${BASE}/v1/agent/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ goal }),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`agent stream failed: ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) >= 0) {
      const frame = buffer.slice(0, sep).trim();
      buffer = buffer.slice(sep + 2);
      if (frame.startsWith("data:")) {
        try {
          onEvent(JSON.parse(frame.slice(5).trim()) as AgentStreamEvent);
        } catch {
          /* ignore malformed keep-alive frames */
        }
      }
    }
  }
}

export const isLiveBackend = Boolean(BASE);
