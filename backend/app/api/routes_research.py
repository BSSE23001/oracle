"""
Research session routes, this is where the "watch every agent think"
demo feature lives (`GET /{session_id}/stream`).

Flow:
  1. POST /api/research             -> creates a session row, enqueues
                                       run_research_task, returns immediately
  2. GET  /api/research/{id}/stream -> SSE stream of everything that
                                       happens, live, replaying history
                                       first so a (re)connecting client
                                       never misses anything
  3. (graph pauses for human review; status becomes "awaiting_review",
      and a `plan_review_required` event is published)
  4. POST /api/research/{id}/review -> enqueues resume_research_task
  5. ... stream continues until a `session_completed`/`session_failed` event
"""

from __future__ import annotations

import json
import uuid

import redis.asyncio as redis_async
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.schemas import (
    ReportSummary,
    ResearchCreateRequest,
    ResearchCreateResponse,
    ResearchSessionResponse,
    ReviewDecisionRequest,
)
from app.config import settings
from app.db import crud
from app.db.session import get_db
from app.tasks.research_tasks import resume_research_task, run_research_task

router = APIRouter(prefix="/api/research", tags=["research"])

_TERMINAL_EVENT_TYPES = {"session_completed", "session_failed"}


@router.post("", response_model=ResearchCreateResponse, status_code=201)
async def start_research(
    payload: ResearchCreateRequest, db: AsyncSession = Depends(get_db)
) -> ResearchCreateResponse:
    session = await crud.create_session(db, payload.query)
    run_research_task.delay(str(session.id), payload.query)
    return ResearchCreateResponse(session_id=session.id, status=session.status)


@router.get("", response_model=list[ResearchSessionResponse])
async def list_research_sessions(
    limit: int = 20, offset: int = 0, db: AsyncSession = Depends(get_db)
) -> list[ResearchSessionResponse]:
    sessions = await crud.list_sessions(db, limit=limit, offset=offset)
    return [_session_to_response(s, report=None) for s in sessions]


@router.get("/{session_id}", response_model=ResearchSessionResponse)
async def get_research_session(
    session_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> ResearchSessionResponse:
    session = await crud.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Research session not found")
    report_row = await crud.get_report_by_session(db, session_id)
    return _session_to_response(session, report_row)


@router.post("/{session_id}/review", status_code=202)
async def submit_plan_review(
    session_id: uuid.UUID,
    payload: ReviewDecisionRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    session = await crud.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Research session not found")
    if session.status != "awaiting_review":
        raise HTTPException(
            status_code=409,
            detail=f"Session is not awaiting review (current status: {session.status})",
        )

    decision = {"approved": payload.approved, "feedback": payload.feedback or ""}
    resume_research_task.delay(str(session_id), decision)
    return {"session_id": str(session_id), "status": "review_submitted"}


@router.get("/{session_id}/stream")
async def stream_research_events(
    session_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> EventSourceResponse:
    session = await crud.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Research session not found")

    return EventSourceResponse(_event_generator(str(session_id), db))


async def _event_generator(session_id: str, db: AsyncSession):
    # Note: `db` is only used once below, to fetch history before
    # subscribing to live events, but FastAPI's `Depends(get_db)` keeps
    # this connection checked out from the pool for the entire lifetime of
    # this generator (i.e. the whole SSE stream, potentially minutes). For
    # a single-demo-instance deployment that's a non-issue; under real
    # concurrent load, increase the asyncpg pool size in `db/session.py`
    # or fetch history through a short-lived session instead of the
    # request-scoped one.
    redis_client = redis_async.Redis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis_client.pubsub()
    channel = f"oracle:events:{session_id}"

    # Subscribe BEFORE reading history, so there's no gap between "read
    # what already happened" and "start listening for what happens next"
    # that a fast-moving Celery task could publish into and be missed.
    await pubsub.subscribe(channel)
    try:
        last_sequence = 0
        history = await crud.list_agent_events(db, uuid.UUID(session_id))
        for event in history:
            last_sequence = max(last_sequence, event.sequence)
            yield _sse_message(
                event.event_type, event.node_name, event.payload, event.sequence
            )
            if event.event_type in _TERMINAL_EVENT_TYPES:
                return

        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            payload = json.loads(message["data"])
            if payload["sequence"] <= last_sequence:
                continue  # already sent during the history replay above
            yield _sse_message(
                payload["type"],
                payload.get("node"),
                payload.get("data"),
                payload["sequence"],
            )
            if payload["type"] in _TERMINAL_EVENT_TYPES:
                return
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        await redis_client.aclose()


def _sse_message(event_type: str, node_name: str | None, data, sequence: int) -> dict:
    return {
        "event": event_type,
        "id": str(sequence),
        "data": json.dumps({"node": node_name, "data": data}, default=str),
    }


def _session_to_response(session, report) -> ResearchSessionResponse:
    return ResearchSessionResponse(
        id=session.id,
        query=session.query,
        status=session.status,
        plan=session.plan,
        error_message=session.error_message,
        created_at=session.created_at,
        updated_at=session.updated_at,
        report=(
            ReportSummary.model_validate(report, from_attributes=True)
            if report
            else None
        ),
    )
