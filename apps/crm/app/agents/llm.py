"""LLM client abstraction.

The runtime depends only on the `LLMClient` protocol, so we can build and test the whole agent
with a deterministic `ScriptedLLM` today and drop in the real Anthropic-backed client (Opus for
planning, Haiku for bulk) once `ANTHROPIC_API_KEY` is configured — without touching the runtime.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class LLMResponse:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict = field(default_factory=dict)  # {"input": int, "output": int}

    @property
    def is_final(self) -> bool:
        return not self.tool_calls


class LLMClient(Protocol):
    async def respond(
        self, *, system: str, messages: list[dict], tools: list[dict]
    ) -> LLMResponse: ...


class ScriptedLLM:
    """Deterministic stand-in for tests: returns queued responses in order."""

    def __init__(self, responses: list[LLMResponse]):
        self._responses = list(responses)
        self.calls = 0

    async def respond(self, *, system, messages, tools) -> LLMResponse:
        if self.calls >= len(self._responses):
            raise AssertionError("ScriptedLLM ran out of responses")
        response = self._responses[self.calls]
        self.calls += 1
        return response


class AnthropicLLM:
    """Production client — calls the Anthropic Messages API via the official SDK.

    Maps the SDK response format back to our thin LLMResponse dataclass so the runtime
    stays SDK-agnostic and fully unit-testable with ScriptedLLM.
    """

    def __init__(self, model: str, api_key: str):
        self.model = model
        self.api_key = api_key
        # Lazy import — only pay the cost when we actually have a key.
        import anthropic

        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def respond(self, *, system, messages, tools) -> LLMResponse:
        response = await self._client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=messages,
            tools=tools,
        )

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        args=block.input if isinstance(block.input, dict) else {},
                    )
                )

        return LLMResponse(
            text="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            usage={
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens,
            },
        )
