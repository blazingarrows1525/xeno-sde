import {
  buildAgentRun,
  MOCK_CALIBRATION,
  MOCK_CAMPAIGNS,
  MOCK_CHANNEL_ROI,
  mockCampaignDetail,
} from "./mock";

// When NEXT_PUBLIC_API_URL is set, these swap to real fetch() calls against the CRM service.
// Until the backend (Neon-backed) is wired, they resolve mock data so the UI is fully demoable.
const BASE = process.env.NEXT_PUBLIC_API_URL;

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function listCampaigns() {
  await delay(120);
  return MOCK_CAMPAIGNS;
}

export async function getCampaign(id: string) {
  await delay(120);
  return mockCampaignDetail(id);
}

export async function getChannelRoi() {
  await delay(120);
  return MOCK_CHANNEL_ROI;
}

export async function getCalibration() {
  await delay(120);
  return MOCK_CALIBRATION;
}

export function runAgent(goal: string) {
  // Real impl: POST /v1/agent/runs then stream GET /v1/agent/runs/{id}/stream (SSE).
  return buildAgentRun(goal);
}

export const isLiveBackend = Boolean(BASE);
