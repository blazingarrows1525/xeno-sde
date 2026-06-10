"""Segment tool — the model proposes a Segment DSL; we compile + (optionally) size it."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from pydantic import BaseModel

from app.agents.tools.base import Tool
from app.segments import SegmentDSL, compile_segment
from app.segments.dsl import FIELDS, OPS_BY_TYPE


def _field_catalog() -> str:
    """Human-readable field + operator catalog, generated from the DSL allowlist so the
    tool description can never drift out of sync with what the compiler actually accepts."""
    by_type: dict[str, list[str]] = {}
    for name, fdef in FIELDS.items():
        by_type.setdefault(fdef.type, []).append(name)
    fields = "; ".join(
        f"{t} [{', '.join(sorted(names))}]" for t, names in sorted(by_type.items())
    )
    ops = "; ".join(
        f"{t}: {', '.join(sorted(ops))}" for t, ops in sorted(OPS_BY_TYPE.items())
    )
    return fields, ops


_FIELDS_STR, _OPS_STR = _field_catalog()


class BuildSegmentArgs(BaseModel):
    dsl: SegmentDSL


class BuildSegmentTool(Tool):
    name = "build_segment"
    description = (
        "Validate a Segment DSL document and return the compiled SQL plus the estimated "
        "audience size (count of matching customers). You propose a typed DSL; you NEVER "
        "write SQL. Use ONLY these fields — anything else is rejected:\n"
        f"  fields by type -> {_FIELDS_STR}\n"
        f"  operators by type -> {_OPS_STR}\n"
        "Notes: numeric time fields are 'days since', so days_since_last_order >= 60 means "
        "'last ordered 60+ days ago'; ltv/total_spend are in INR; booleans use is_true/"
        "is_false; in/not_in take a non-empty list. "
        'DSL shape: {"version":1,"match":"all"|"any","rules":['
        '{"field":"<field>","op":"<op>","value":<scalar|list>}, '
        '{"match":"any","rules":[<nested>]}]}'
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
