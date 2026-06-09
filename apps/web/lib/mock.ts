import type {
  AgentPlan,
  AgentStep,
  CalibrationPoint,
  CampaignDetail,
  CampaignSummary,
  ChannelRoi,
} from "./types";

// NOTE: scaffold data. lib/api.ts returns these until the backend (Neon-backed) is wired.

export const MOCK_CAMPAIGNS: CampaignSummary[] = [
  {
    id: "win-back-60d",
    name: "Win-back · 60-day dormant",
    goal: "Bring back customers who haven't ordered in 60 days and maximize ROI",
    channel: "whatsapp",
    status: "completed",
    audience: 4182,
    sent: 4182,
    converted: 261,
    revenue: 712400,
    roas: 6.8,
    createdAt: "2026-06-09",
  },
  {
    id: "vip-cross-sell",
    name: "VIP cross-sell · new arrivals",
    goal: "Show new arrivals to high-LTV repeat buyers",
    channel: "email",
    status: "sending",
    audience: 1890,
    sent: 1204,
    converted: 73,
    revenue: 245900,
    roas: 4.1,
    createdAt: "2026-06-10",
  },
  {
    id: "first-repeat",
    name: "First-to-second order nudge",
    goal: "Convert one-time buyers into repeat customers",
    channel: "sms",
    status: "pending_approval",
    audience: 2640,
    sent: 0,
    converted: 0,
    revenue: 0,
    roas: 0,
    createdAt: "2026-06-10",
  },
];

export function mockCampaignDetail(id: string): CampaignDetail {
  const base = MOCK_CAMPAIGNS.find((c) => c.id === id) ?? MOCK_CAMPAIGNS[0];
  const sent = base.sent || base.audience;
  return {
    ...base,
    funnel: {
      sent,
      delivered: Math.round(sent * 0.92),
      opened: Math.round(sent * 0.71),
      read: Math.round(sent * 0.6),
      clicked: Math.round(sent * 0.19),
      converted: base.converted || Math.round(sent * 0.062),
      failed: Math.round(sent * 0.08),
    },
    predicted: {
      audience: base.audience,
      deliveredRate: 0.92,
      openRate: 0.78,
      clickRate: 0.19,
      convertRate: 0.062,
      revenue: base.revenue || 720000,
      roas: 7.1,
    },
    variants: [
      { variant: "A", sent: Math.round(sent / 2), clicked: Math.round(sent * 0.1), converted: Math.round((base.converted || 200) * 0.45) },
      { variant: "B", sent: Math.round(sent / 2), clicked: Math.round(sent * 0.09), converted: Math.round((base.converted || 200) * 0.55) },
    ],
    timeline: [
      { customer: "Aisha K.", variant: "B", state: "converted", at: "10:14" },
      { customer: "Rohan M.", variant: "A", state: "clicked", at: "10:12" },
      { customer: "Neha S.", variant: "B", state: "read", at: "10:11" },
      { customer: "Vikram R.", variant: "A", state: "delivered", at: "10:09" },
      { customer: "Priya D.", variant: "B", state: "failed", at: "10:08" },
    ],
  };
}

export const MOCK_CHANNEL_ROI: ChannelRoi[] = [
  { channel: "whatsapp", deliverability: 0.92, convertRate: 0.062, cpa: 41, roas: 6.8 },
  { channel: "rcs", deliverability: 0.9, convertRate: 0.048, cpa: 58, roas: 4.6 },
  { channel: "email", deliverability: 0.95, convertRate: 0.026, cpa: 73, roas: 3.4 },
  { channel: "sms", deliverability: 0.88, convertRate: 0.021, cpa: 92, roas: 2.7 },
];

export const MOCK_CALIBRATION: CalibrationPoint[] = [
  { campaign: "C1", predictedRoas: 5.2, actualRoas: 3.9 },
  { campaign: "C2", predictedRoas: 6.0, actualRoas: 5.1 },
  { campaign: "C3", predictedRoas: 6.4, actualRoas: 6.0 },
  { campaign: "C4", predictedRoas: 7.1, actualRoas: 6.8 },
  { campaign: "C5", predictedRoas: 6.9, actualRoas: 6.7 },
];

export function buildAgentRun(goal: string): { steps: AgentStep[]; plan: AgentPlan } {
  const steps: AgentStep[] = [
    { kind: "thought", title: "Parsed goal", detail: "objective = win-back · KPI to maximize = ROAS" },
    { kind: "tool_call", title: "query_audience_stats", tool: "query_audience_stats" },
    {
      kind: "tool_result",
      title: "4,182 dormant shoppers",
      detail: "71% WhatsApp-reachable · avg LTV ₹3,400 · median recency 84 days",
    },
    {
      kind: "thought",
      title: "Recalled a past learning",
      detail: "WhatsApp beat SMS 2.3× for win-back on high-LTV segments",
    },
    { kind: "tool_call", title: "build_segment", tool: "build_segment", detail: "days_since_last_order ≥ 60 AND total_orders ≥ 1 AND whatsapp_opt_in" },
    { kind: "tool_result", title: "Segment valid · 4,182 customers", detail: "compiled to parameterized SQL" },
    { kind: "tool_call", title: "recommend_channel", tool: "recommend_channel" },
    { kind: "tool_result", title: "WhatsApp wins", detail: "predicted ROAS 7.1× vs SMS 3.0× vs Email 2.4×" },
    { kind: "tool_call", title: "draft_message", tool: "draft_message", detail: "2 variants, brand voice, personalization tokens" },
    { kind: "tool_call", title: "estimate_campaign_outcome", tool: "estimate_campaign_outcome" },
    { kind: "tool_result", title: "Predicted ROAS 7.1×", detail: "64% delivered · 19% click · 6.2% convert · ~₹720k revenue" },
    { kind: "plan", title: "Assembled a campaign plan", detail: "ready for your approval" },
    { kind: "final", title: "Plan ready", detail: "approve to launch through the channel service" },
  ];

  const plan: AgentPlan = {
    segmentName: "60-day dormant · WhatsApp-reachable",
    channel: "whatsapp",
    audience: 4182,
    variants: [
      { label: "A", body: "Hi {{first_name}}, we miss you! Here's 15% off your favourite {{last_category}} — today only." },
      { label: "B", body: "{{first_name}}, your cart misses you 👀 Come back for 15% off + free delivery this weekend." },
    ],
    predicted: {
      audience: 4182,
      deliveredRate: 0.92,
      openRate: 0.78,
      clickRate: 0.19,
      convertRate: 0.062,
      revenue: 720000,
      roas: 7.1,
    },
    rationale:
      "WhatsApp maximizes predicted ROAS for this dormant, high-LTV segment based on prior win-back campaigns. Two variants test urgency vs. curiosity framing. Goal: " +
      goal,
  };

  return { steps, plan };
}
