"""Agent runtime: tool dispatch, the approval gate, step cap, and error handling.

All driven by a scripted LLM — no API key or database required.
"""
from pydantic import BaseModel

from app.agents.llm import FallbackLLM, LLMResponse, ScriptedLLM, ToolCall
from app.agents.runtime import AgentRuntime
from app.agents.tools.base import Tool, ToolRegistry
from app.agents.tools.campaign_tools import LaunchCampaignTool
from app.agents.tools.segment_tools import BuildSegmentTool


class EchoArgs(BaseModel):
    value: str


class EchoTool(Tool):
    name = "echo"
    description = "echo a value back"
    Args = EchoArgs

    async def run(self, args: EchoArgs) -> dict:
        return {"echo": args.value}


def _registry(*tools) -> ToolRegistry:
    reg = ToolRegistry()
    for tool in tools:
        reg.register(tool)
    return reg


async def test_runs_tool_then_finishes():
    llm = ScriptedLLM(
        [
            LLMResponse(tool_calls=[ToolCall("t1", "echo", {"value": "hi"})]),
            LLMResponse(text="all done"),
        ]
    )
    result = await AgentRuntime(llm, _registry(EchoTool())).run("do it")
    assert result.status == "completed"
    assert result.final_text == "all done"
    kinds = [(s.type, s.tool_name) for s in result.steps]
    assert ("tool_call", "echo") in kinds
    assert ("tool_result", "echo") in kinds


async def test_approval_gate_blocks_then_allows_launch():
    blocked = await AgentRuntime(
        llm=ScriptedLLM([LLMResponse(tool_calls=[ToolCall("t1", "launch_campaign", {"campaign_id": "c1"})])]),
        registry=_registry(LaunchCampaignTool()),
    ).run("launch it", approved=False)
    assert blocked.status == "awaiting_approval"

    allowed = await AgentRuntime(
        llm=ScriptedLLM(
            [
                LLMResponse(tool_calls=[ToolCall("t1", "launch_campaign", {"campaign_id": "c1"})]),
                LLMResponse(text="launched"),
            ]
        ),
        registry=_registry(LaunchCampaignTool()),
    ).run("launch it", approved=True)
    assert allowed.status == "completed"
    assert any(s.type == "tool_result" and (s.output or {}).get("launched") for s in allowed.steps)


async def test_max_steps_is_enforced():
    llm = ScriptedLLM(
        [LLMResponse(tool_calls=[ToolCall(f"t{i}", "echo", {"value": "x"})]) for i in range(3)]
    )
    result = await AgentRuntime(llm, _registry(EchoTool()), max_steps=3).run("loop forever")
    assert result.status == "max_steps"


async def test_unknown_tool_is_recorded_and_run_continues():
    llm = ScriptedLLM(
        [
            LLMResponse(tool_calls=[ToolCall("t1", "does_not_exist", {})]),
            LLMResponse(text="ok"),
        ]
    )
    result = await AgentRuntime(llm, _registry(EchoTool())).run("x")
    assert result.status == "completed"
    assert any(s.type == "error" for s in result.steps)


async def test_build_segment_tool_compiles_and_counts():
    async def fake_counter(where_sql: str, params: dict) -> int:
        return 4182

    tool = BuildSegmentTool(counter=fake_counter)
    out = await tool.run(
        tool.Args(dsl={"rules": [{"field": "days_since_last_order", "op": "gte", "value": 60}]})
    )
    assert out["estimated_size"] == 4182
    assert "EXTRACT(EPOCH" in out["compiled_where"]
    assert out["params"] == {"p0": 60}


class _RaisingLLM:
    """Fake client that always fails, optionally carrying an HTTP-style status code."""

    def __init__(self, status_code: int | None = None):
        self.status_code = status_code

    async def respond(self, *, system, messages, tools) -> LLMResponse:
        exc = RuntimeError(f"simulated failure (status={self.status_code})")
        if self.status_code is not None:
            exc.status_code = self.status_code  # duck-typed capacity signal
        raise exc


class _OkLLM:
    def __init__(self, text: str):
        self.text = text
        self.calls = 0

    async def respond(self, *, system, messages, tools) -> LLMResponse:
        self.calls += 1
        return LLMResponse(text=self.text)


async def test_fallback_switches_models_when_primary_is_rate_limited():
    primary = _RaisingLLM(status_code=429)  # Haiku "runs out"
    secondary = _OkLLM("served by opus")
    llm = FallbackLLM([primary, secondary], labels=["haiku", "opus"])
    out = await llm.respond(system="s", messages=[], tools=[])
    assert out.text == "served by opus"
    assert secondary.calls == 1


async def test_fallback_does_not_mask_a_real_request_error():
    # A 400 is a bad request — retrying on another model fails identically, so it must raise.
    primary = _RaisingLLM(status_code=400)
    secondary = _OkLLM("should not be reached")
    llm = FallbackLLM([primary, secondary])
    try:
        await llm.respond(system="s", messages=[], tools=[])
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected the 400 to propagate, not fall back")
    assert secondary.calls == 0


async def test_fallback_raises_last_error_when_all_models_exhausted():
    llm = FallbackLLM([_RaisingLLM(429), _RaisingLLM(503)])
    try:
        await llm.respond(system="s", messages=[], tools=[])
    except RuntimeError as exc:
        assert "503" in str(exc)
    else:
        raise AssertionError("expected the final error to propagate")


async def test_build_segment_tool_bad_dsl_surfaces_as_error_output():
    llm = ScriptedLLM(
        [
            LLMResponse(
                tool_calls=[
                    ToolCall("t1", "build_segment", {"dsl": {"rules": [{"field": "evil", "op": "eq", "value": 1}]}})
                ]
            ),
            LLMResponse(text="handled"),
        ]
    )
    result = await AgentRuntime(llm, _registry(BuildSegmentTool())).run("segment")
    assert result.status == "completed"
    assert any(
        s.type == "tool_result" and s.tool_name == "build_segment" and "error" in (s.output or {})
        for s in result.steps
    )
