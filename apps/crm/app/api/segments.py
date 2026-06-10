"""Segment endpoints. `/preview` is the single audited path the agent and the UI both use."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models.segment import Segment, SegmentMember
from app.segments import SegmentDSL, compile_segment

router = APIRouter(tags=["segments"])


# ── schemas ──────────────────────────────────────────────────────────────

class PreviewRequest(BaseModel):
    dsl: SegmentDSL


class PreviewResponse(BaseModel):
    compiled_where: str
    params: dict[str, Any]
    count_sql: str
    estimated_size: int | None = None


class CreateSegmentRequest(BaseModel):
    name: str
    dsl: SegmentDSL
    materialize: bool = False  # if True, snapshot member IDs immediately


class SegmentOut(BaseModel):
    id: str
    name: str
    dsl: dict[str, Any]
    compiled_sql: str | None
    estimated_size: int | None
    status: str
    created_at: str


# ── helpers ──────────────────────────────────────────────────────────────

async def _count_segment(session: AsyncSession, compiled: Any) -> int:
    """Run the compiled count query against the live customers table."""
    stmt = text(compiled.count_sql())
    for k, v in compiled.params.items():
        stmt = stmt.bindparams(**{k: v})
    result = await session.scalar(stmt)
    return result or 0


# ── routes ───────────────────────────────────────────────────────────────

@router.post("/segments/preview", response_model=PreviewResponse)
async def preview_segment(
    req: PreviewRequest, session: AsyncSession = Depends(get_session)
) -> PreviewResponse:
    """Compile a Segment DSL to SQL and return the live audience count."""
    compiled = compile_segment(req.dsl)
    count = await _count_segment(session, compiled)
    return PreviewResponse(
        compiled_where=compiled.where_sql,
        params=compiled.params,
        count_sql=compiled.count_sql(),
        estimated_size=count,
    )


@router.post("/segments", response_model=SegmentOut, status_code=201)
async def create_segment(
    req: CreateSegmentRequest, session: AsyncSession = Depends(get_session)
) -> SegmentOut:
    """Persist a named segment. Optionally materialize membership for campaign targeting."""
    compiled = compile_segment(req.dsl)
    count = await _count_segment(session, compiled)

    segment = Segment(
        name=req.name,
        dsl=req.dsl.model_dump(),
        compiled_sql=compiled.where_sql,
        estimated_size=count,
        status="active",
    )
    session.add(segment)
    await session.flush()

    if req.materialize:
        ids_sql = text(compiled.select_ids_sql())
        for k, v in compiled.params.items():
            ids_sql = ids_sql.bindparams(**{k: v})
        rows = await session.execute(ids_sql)
        members = [
            SegmentMember(segment_id=segment.id, customer_id=row[0])
            for row in rows
        ]
        session.add_all(members)

    await session.commit()
    return SegmentOut(
        id=str(segment.id),
        name=segment.name,
        dsl=segment.dsl,
        compiled_sql=segment.compiled_sql,
        estimated_size=segment.estimated_size,
        status=segment.status,
        created_at=segment.created_at.isoformat(),
    )


@router.get("/segments", response_model=list[SegmentOut])
async def list_segments(session: AsyncSession = Depends(get_session)) -> list[SegmentOut]:
    from sqlalchemy import select

    rows = await session.execute(
        select(Segment).order_by(Segment.created_at.desc())
    )
    return [
        SegmentOut(
            id=str(s.id),
            name=s.name,
            dsl=s.dsl,
            compiled_sql=s.compiled_sql,
            estimated_size=s.estimated_size,
            status=s.status,
            created_at=s.created_at.isoformat(),
        )
        for s in rows.scalars()
    ]
