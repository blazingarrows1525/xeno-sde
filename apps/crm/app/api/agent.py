"""Agent endpoint — streams the reasoning trace as Server-Sent Events.

POST /v1/agent/run  { "goal": "..." }
→ SSE stream of { step_type, tool_name, content, ... } lines
→ final event: { type: "plan", plan: { ... } } with predicted KPIs
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm import AnthropicLLM, LLMClient, ScriptedLLM
from app.agents.runtime import AgentRuntime
from app.agents.tools.base import ToolRegistry
from app.agents.tools.segment_tools import BuildSegmentTool
from app.agents.tools.campaign_tools import LaunchCampaignTool
from app.core.config import settings
from app.core.db import get_session
from app.models.agent import AgentRun, AgentStep
from app.segments import compile_segment

router = APIRouter(tags=["agent"])


class AgentRequest(BaseModel):
    goal: str
    approved: bool = False


def _build_llm() -> LLMClient:
    """Use real LLM if API key is set, otherwise fall back to scripted."""
    if settings.anthropic_api_key:
        return AnthropicLLM(
            api_key=settings.anthropic_api_key,
            model=settings.bulk_model,
        )
    # Fallback for demo without key
    from app.agents.llm import LLMResponse, ToolCall
    return ScriptedLLM(responses=[
        LLMResponse(
            content="Let me analyze the customer base and build a targeted segment.",
            tool_calls=[ToolCall(
                id="tc1",
                name="build_segment",
                args={"dsl": {
                    "match": "all",
                    "rules": [
                        {"field": "last_order_at", "op": "lt", "value": "2026-04-01T00:00:00Z"},
                        {"field": "total_orders", "op": "gte", "value": 2},
                    ],
                }},
            )],
        ),
        LLMResponse(
            content="I found a good segment. Now let me propose a campaign to re-engage them.",
            tool_calls=[ToolCall(
                id="tc2",
                name="launch_campaign",
                args={
                    "name": "Win-back: Dormant Loyal",
                    "channel": "whatsapp",
                    "segment_dsl": {
                        "match": "all",
                        "rules": [
                            {"field": "last_order_at", "op": "lt", "value": "2026-04-01T00:00:00Z"},
                            {"field": "total_orders", "op": "gte", "value": 2},
                        ],
                    },
                },
            )],
        ),
        LLMResponse(
            content="Campaign plan is ready for approval.",
            tool_calls=[],
        ),
    ])


async def _count_segment(dsl_dict: dict) -> int:
    """Quick count for the build_segment tool — uses a fresh session."""
    from app.segments.dsl import SegmentDSL
    from sqlalchemy import text

    parsed = SegmentDSL.model_validate(dsl_dict)
    compiled = compile_segment(parsed)
    from app.core.db import get_sessionmaker
    async with get_sessionmaker()() as session:
        stmt = text(compiled.count_sql())
        for k, v in compiled.params.items():
            stmt = stmt.bindparams(**{k: v})
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
        result = await runtime.run(req.goal, approved=req.approved)
        for step in result.steps:
            data = {
                "kind": step.type,
                "step_no": step.step_no,
            }
            if step.tool_name:
                data["tool"] = step.tool_name
            if step.input:
                data["tool_input"] = step.input
            if step.output:
                data["tool_output"] = step.output
            yield f"data: {json.dumps(data, default=str)}\n\n"

        # Final summary event
        summary = {
            "type": "complete",
            "status": result.status,
            "steps_taken": len(result.steps),
            "final_text": result.final_text,
        }
        yield f"data: {json.dumps(summary, default=str)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
