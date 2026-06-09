"""Segment tool — the model proposes a Segment DSL; we compile + (optionally) size it."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from pydantic import BaseModel

from app.agents.tools.base import Tool
from app.segments import SegmentDSL, compile_segment


class BuildSegmentArgs(BaseModel):
    dsl: SegmentDSL


class BuildSegmentTool(Tool):
    name = "build_segment"
    description = (
        "Validate a Segment DSL and return the compiled SQL plus the estimated audience size. "
        "The model proposes the DSL; it never writes SQL directly."
    )
    Args = BuildSegmentArgs

    def __init__(self, counter: Callable[[str, dict], Awaitable[int]] | None = None):
        # `counter(where_sql, params) -> int` runs the COUNT against the DB; injected so the
        # tool stays unit-testable and DB-agnostic.
        self._counter = counter

    async def run(self, args: BuildSegmentArgs) -> dict:
        compiled = compile_segment(args.dsl)
        size = await self._counter(compiled.where_sql, compiled.params) if self._counter else None
        return {
            "compiled_where": compiled.where_sql,
            "params": compiled.params,
            "estimated_size": size,
        }
