"""Tool abstraction. A tool is the ONLY way the model touches the world.

Every tool declares a Pydantic `Args` model, so arguments emitted by the LLM are validated
before anything runs. `requires_approval` lets the runtime enforce the human gate in code
(not in the prompt) — e.g. `launch_campaign` cannot fire without approval.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class Tool(ABC):
    name: str
    description: str
    Args: type[BaseModel]
    requires_approval: bool = False

    @abstractmethod
    async def run(self, args: BaseModel) -> dict: ...

    def schema(self) -> dict:
        """JSON schema in the shape Anthropic tool-use expects."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.Args.model_json_schema(),
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def schemas(self) -> list[dict]:
        return [tool.schema() for tool in self._tools.values()]

    async def dispatch(self, name: str, raw_args: dict) -> dict:
        tool = self._tools[name]
        args = tool.Args(**raw_args)  # Pydantic validation; raises on malformed args
        return await tool.run(args)
