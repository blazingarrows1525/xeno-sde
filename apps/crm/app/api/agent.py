"""Agent endpoint — streams the reasoning trace as Server-Sent Events.

POST /v1/agent/run  { "goal": "..." }
→ SSE stream of { step_type, tool_name, content, ... } lines
→ final event: { type: "plan", plan: { ... } } with predicted KPIs
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm import AnthropicLLM, FallbackLLM, LLMClient, ScriptedLLM
from app.agents.runtime import AgentRuntime
from app.agents.tools.base import ToolRegistry
from app.agents.tools.segment_tools import BuildSegmentTool
from app.agents.tools.campaign_tools import LaunchCampaignTool
from app.core.config import settings
from app.core.db import get_session
from app.models.agent import AgentRun, AgentStep

router = APIRouter(tags=["agent"])


class AgentRequest(BaseModel):
    goal: str
    approved: bool = False


def _build_llm() -> LLMClient:
    """Real LLM when a key is set, else a scripted stand-in.

    With a key we build a fallback chain: Haiku 4.5 (bulk_model) serves first for speed and
    cost; if it is rate-limited or unavailable, Opus 4.8 (planner_model) transparently takes
    over for that request. The SDK already retries transient 429/5xx a couple of times before
    we even see the error, so reaching the fallback means the primary is genuinely exhausted.
    """
    if settings.anthropic_api_key:
        key = settings.anthropic_api_key
        return FallbackLLM(
            clients=[
                AnthropicLLM(api_key=key, model=settings.bulk_model),
                AnthropicLLM(api_key=key, model=settings.planner_model),
            ],
            labels=[settings.bulk_model, settings.planner_model],
        )
    # Fallback for demo without key
    from app.agents.llm import LLMResponse, ToolCall
    return ScriptedLLM(responses=[
        LLMResponse(
            text="Let me analyze the customer base and build a targeted segment.",
            tool_calls=[ToolCall(
                id="tc1",
                name="build_segment",
                args={"dsl": {
                    "match": "all",
                    "rules": [
                        {"field": "days_since_last_order", "op": "gte", "value": 60},
                        {"field": "total_orders", "op": "gte", "value": 2},
                    ],
                }},
            )],
        ),
        LLMResponse(
            text="I found a good segment. Now let me propose a campaign to re-engage them.",
            tool_calls=[ToolCall(
                id="tc2",
                name="launch_campaign",
                args={"campaign_id": "proposed-winback"},
            )],
        ),
        LLMResponse(
            text="Campaign plan is ready for approval.",
            tool_calls=[],
        ),
    ])


async def _count_segment(where_sql: str, params: dict) -> int:
    """Live audience count for the build_segment tool.

    Matches the tool's injected-counter contract: counter(where_sql, params) -> int.
    The compiler already produced a parameterized WHERE clause; we bind values safely.
    """
    from sqlalchemy import text
    from app.core.db import get_sessionmaker

    stmt = text(f"SELECT count(*) AS n FROM customers WHERE {where_sql}")
    for k, v in params.items():
        stmt = stmt.bindparams(**{k: v})
    async with get_sessionmaker()() as session:
        return (await session.scalar(stmt)) or 0


@router.post("/agent/run")
async def run_agent(req: AgentRequest) -> StreamingResponse:
    """Stream agent reasoning as SSE events."""
    llm = _build_llm()

    # Register tools with live DB counter
    registry = ToolRegistry()
    registry.register(BuildSegmentTool(counter=_count_segment))
    registry.register(LaunchCampaignTool())

    runtime = AgentRuntime(
        llm=llm,
        registry=registry,
        max_steps=settings.agent_max_steps,
    )

    async def event_stream():
        # Stream each reasoning step the moment the agent produces it (genuine glass box).
        last_kind = "max_steps"
        steps_taken = 0
        async for step in runtime.run_stream(req.goal, approved=req.approved):
            last_kind = step.type
            steps_taken += 1
            data = {"kind": step.type, "step_no": step.step_no}
            if step.tool_name:
                data["tool"] = step.tool_name
            if step.input:
                data["tool_input"] = step.input
            if step.output:
                data["tool_output"] = step.output
            yield f"data: {json.dumps(data, default=str)}\n\n"
            await asyncio.sleep(0.2)  # smooth the reveal in the UI

        status = {"final": "completed", "awaiting_approval": "awaiting_approval"}.get(
            last_kind, "max_steps"
        )
        yield f"data: {json.dumps({'type': 'complete', 'status': status, 'steps_taken': steps_taken})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
