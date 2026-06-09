"""Segment endpoints. `/preview` is the single audited path the agent and the UI both use."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.segments import SegmentDSL, compile_segment

router = APIRouter(tags=["segments"])


class PreviewRequest(BaseModel):
    dsl: SegmentDSL


class PreviewResponse(BaseModel):
    compiled_where: str
    params: dict[str, Any]
    count_sql: str
    estimated_size: int | None = None
    note: str | None = None


@router.post("/segments/preview", response_model=PreviewResponse)
async def preview_segment(req: PreviewRequest) -> PreviewResponse:
    """Compile a Segment DSL to SQL and (once the DB is wired) estimate the audience size.

    Invalid DSL is rejected by FastAPI/Pydantic with a 422 before reaching this handler — the
    same validation the agent's `build_segment` tool relies on.
    """
    compiled = compile_segment(req.dsl)
    return PreviewResponse(
        compiled_where=compiled.where_sql,
        params=compiled.params,
        count_sql=compiled.count_sql(),
        estimated_size=None,
        note="DB not wired yet — provision Postgres to populate estimated_size. "
        "Compiled SQL + bound params are shown for audit.",
    )
