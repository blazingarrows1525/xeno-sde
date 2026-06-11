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
