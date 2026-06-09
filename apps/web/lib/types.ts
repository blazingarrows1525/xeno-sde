export type EventType =
  | "sent"
  | "delivered"
  | "opened"
  | "read"
  | "clicked"
  | "converted"
  | "failed";

export type Channel = "whatsapp" | "sms" | "email" | "rcs";

export interface FunnelStat {
  sent: number;
  delivered: number;
  opened: number;
  read: number;
  clicked: number;
  converted: number;
  failed: number;
}

export interface PredictedKpis {
  audience: number;
  deliveredRate: number;
  openRate: number;
  clickRate: number;
  convertRate: number;
  revenue: number;
  roas: number;
}

export interface CampaignSummary {
  id: string;
  name: string;
  goal: string;
  channel: Channel;
  status: "completed" | "sending" | "pending_approval" | "draft";
  audience: number;
  sent: number;
  converted: number;
  revenue: number;
  roas: number;
  createdAt: string;
}

export interface VariantStat {
  variant: "A" | "B";
  sent: number;
  clicked: number;
  converted: number;
}

export interface TimelineItem {
  customer: string;
  variant: "A" | "B";
  state: EventType;
  at: string;
}

export interface CampaignDetail extends CampaignSummary {
  funnel: FunnelStat;
  predicted: PredictedKpis;
  variants: VariantStat[];
  timeline: TimelineItem[];
}

export type AgentStepKind = "thought" | "tool_call" | "tool_result" | "plan" | "final";

export interface AgentStep {
  kind: AgentStepKind;
  title: string;
  detail?: string;
  tool?: string;
}

export interface AgentPlan {
  segmentName: string;
  channel: Channel;
  audience: number;
  variants: { label: string; body: string }[];
  predicted: PredictedKpis;
  rationale: string;
}

export interface ChannelRoi {
  channel: Channel;
  deliverability: number;
  convertRate: number;
  cpa: number;
  roas: number;
}

export interface CalibrationPoint {
  campaign: string;
  predictedRoas: number;
  actualRoas: number;
}
