"""LLM client abstraction.

The runtime depends only on the `LLMClient` protocol, so we can build and test the whole agent
with a deterministic `ScriptedLLM` and swap in real Anthropic-backed clients once
`ANTHROPIC_API_KEY` is set — without touching the runtime. `FallbackLLM` chains models so a
primary (Haiku 4.5) serves first and a secondary (Opus 4.8) transparently takes over when the
primary is rate-limited or unavailable.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol

logger = logging.getLogger("kairos.llm")


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


# HTTP statuses where retrying the same request on a *different* model is worthwhile:
# rate limits, overload, and transient server/gateway errors. (400/401/403/404/422 are
# request-level faults that would fail identically on the fallback, so they are excluded.)
_CAPACITY_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}


def _is_capacity_error(exc: Exception) -> bool:
    """True when a model is exhausted or unavailable (rate-limited, overloaded, 5xx, or a
    network failure) — i.e. the cases where falling back to another model can succeed."""
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and (status in _CAPACITY_STATUS or status >= 500):
        return True
    # Connection/timeout errors from the SDK carry no status code.
    try:
        import anthropic

        if isinstance(exc, (anthropic.APITimeoutError, anthropic.APIConnectionError)):
            return True
    except ImportError:
        pass
    return False


class FallbackLLM:
    """A chain of models tried in order, behind the same `LLMClient` protocol.

    The primary model serves every request; if it is rate-limited or unavailable, the next
    model transparently takes over for that request. So Haiku 4.5 absorbs normal load and
    Opus 4.8 steps in the moment Haiku runs out — without the runtime knowing or caring.

    A non-capacity error (e.g. a malformed request) is re-raised immediately rather than
    masked by a fallback that would fail the same way. If every model is exhausted, the last
    error propagates.
    """

    def __init__(self, clients: list[LLMClient], labels: list[str] | None = None):
        if not clients:
            raise ValueError("FallbackLLM requires at least one client")
        self._clients = clients
        self._labels = labels or [f"model[{i}]" for i in range(len(clients))]

    async def respond(self, *, system, messages, tools) -> LLMResponse:
        last_exc: Exception | None = None
        for i, client in enumerate(self._clients):
            try:
                return await client.respond(system=system, messages=messages, tools=tools)
            except Exception as exc:
                last_exc = exc
                is_last = i == len(self._clients) - 1
                if is_last or not _is_capacity_error(exc):
                    raise
                logger.warning(
                    "LLM '%s' unavailable (%s); falling back to '%s'",
                    self._labels[i],
                    type(exc).__name__,
                    self._labels[i + 1],
                )
        # The loop always returns or raises; this is unreachable but satisfies type-checkers.
        raise last_exc  # type: ignore[misc]
