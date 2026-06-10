"""The agent runtime — a bounded ReAct loop with a human-approval gate.

Each iteration: ask the LLM (given the goal + tool schemas); if it emits tool calls, validate
and run them and feed the results back; if it returns text, we're done. Two guardrails:

- **max_steps** caps the loop (no runaway cost / infinite tool loops).
- **requires_approval** tools (e.g. launch_campaign) short-circuit to `awaiting_approval`
  unless the run was started with `approved=True` — the safety gate lives in code, not the prompt.

Every thought/tool_call/tool_result is recorded as an `AgentStepRecord` — that list is exactly
what the UI streams as the glass-box reasoning trace and what we persist to `agent_steps`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.agents.llm import LLMClient
from app.agents.tools.base import ToolRegistry

DEFAULT_SYSTEM = (
    "You are Kairos, an autonomous growth-marketing agent for a D2C brand. Given a goal, you "
    "analyze shoppers, build an audience, choose a channel, draft the message, and predict "
    "outcomes, then assemble a campaign plan for human approval. Use tools for every action and "
    "never invent data. Do not launch a campaign until it has been approved by a human."
)


@dataclass
class AgentStepRecord:
    step_no: int
    type: str  # tool_call | tool_result | final | error | awaiting_approval
    tool_name: str | None = None
    input: dict | None = None
    output: dict | None = None


@dataclass
class AgentResult:
    status: str  # completed | awaiting_approval | max_steps
    final_text: str | None
    steps: list[AgentStepRecord] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0


class AgentRuntime:
    def __init__(
        self,
        llm: LLMClient,
        registry: ToolRegistry,
        *,
        max_steps: int = 16,
        system_prompt: str = DEFAULT_SYSTEM,
    ):
        self.llm = llm
        self.registry = registry
        self.max_steps = max_steps
        self.system_prompt = system_prompt

    async def run(self, goal: str, *, approved: bool = False) -> AgentResult:
        messages: list[dict] = [{"role": "user", "content": goal}]
        steps: list[AgentStepRecord] = []
        tokens_in = tokens_out = 0

        for step_no in range(1, self.max_steps + 1):
            response = await self.llm.respond(
                system=self.system_prompt, messages=messages, tools=self.registry.schemas()
            )
            tokens_in += response.usage.get("input", 0)
            tokens_out += response.usage.get("output", 0)

            if response.is_final:
                steps.append(AgentStepRecord(step_no, "final", output={"text": response.text}))
                return AgentResult("completed", response.text, steps, tokens_in, tokens_out)

            results = []
            for call in response.tool_calls:
                tool = self.registry.get(call.name)
                if tool is None:
                    steps.append(
                        AgentStepRecord(step_no, "error", call.name, call.args, {"error": "unknown tool"})
                    )
                    results.append({"tool_use_id": call.id, "content": {"error": "unknown tool"}})
                    continue

                if tool.requires_approval and not approved:
                    steps.append(AgentStepRecord(step_no, "awaiting_approval", call.name, call.args))
                    return AgentResult("awaiting_approval", None, steps, tokens_in, tokens_out)

                steps.append(AgentStepRecord(step_no, "tool_call", call.name, call.args))
                try:
                    output = await self.registry.dispatch(call.name, call.args)
                except Exception as exc:  # validation/tool error -> report back to the model
                    output = {"error": str(exc)}
                steps.append(AgentStepRecord(step_no, "tool_result", call.name, output=output))
                results.append({"tool_use_id": call.id, "content": output})

            # Format for the Anthropic Messages API:
            # Assistant turn: text blocks + tool_use blocks
            assistant_content = []
            if response.text:
                assistant_content.append({"type": "text", "text": response.text})
            for c in response.tool_calls:
                assistant_content.append({
                    "type": "tool_use", "id": c.id, "name": c.name, "input": c.args
                })
            messages.append({"role": "assistant", "content": assistant_content})

            # User turn: tool_result blocks
            tool_results = [
                {"type": "tool_result", "tool_use_id": r["tool_use_id"],
                 "content": json.dumps(r["content"]) if isinstance(r["content"], dict) else str(r["content"])}
                for r in results
            ]
            messages.append({"role": "user", "content": tool_results})

        return AgentResult("max_steps", None, steps, tokens_in, tokens_out)
