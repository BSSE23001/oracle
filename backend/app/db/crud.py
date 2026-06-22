"""
CRUD helpers. Async functions are used by FastAPI route handlers; the
`_sync` counterparts are used by Celery tasks (see `app/tasks/research_tasks.py`),
which run in plain synchronous worker processes.
"""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.db.models import AgentEvent, Feedback, ResearchReport, ResearchSession

# ── Async (FastAPI) ──────────────────────────────────────────────────────


async def create_session(db: AsyncSession, query: str) -> ResearchSession:
    session = ResearchSession(query=query, status="pending")
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_id: uuid.UUID) -> ResearchSession | None:
    return await db.get(ResearchSession, session_id)


async def list_agent_events(db: AsyncSession, session_id: uuid.UUID, after_sequence: int = 0) -> list[AgentEvent]:
    stmt = (
        select(AgentEvent)
        .where(AgentEvent.session_id == session_id, AgentEvent.sequence > after_sequence)
        .order_by(AgentEvent.sequence)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_sessions(db: AsyncSession, limit: int = 20, offset: int = 0) -> list[ResearchSession]:
    stmt = select(ResearchSession).order_by(ResearchSession.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_report_by_session(db: AsyncSession, session_id: uuid.UUID) -> ResearchReport | None:
    stmt = select(ResearchReport).where(ResearchReport.session_id == session_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_report(db: AsyncSession, report_id: uuid.UUID) -> ResearchReport | None:
    return await db.get(ResearchReport, report_id)


async def list_reports(db: AsyncSession, limit: int = 20, offset: int = 0) -> list[ResearchReport]:
    stmt = select(ResearchReport).order_by(ResearchReport.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_feedback(db: AsyncSession, report_id: uuid.UUID, rating: int, comment: str | None) -> Feedback:
    feedback = Feedback(report_id=report_id, rating=rating, comment=comment)
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback


# ── Sync (Celery) ─────────────────────────────────────────────────────────


def update_session_status_sync(
    db: Session, session_id: str, status: str, *, plan: dict | None = None, error_message: str | None = None
) -> None:
    session = db.get(ResearchSession, uuid.UUID(session_id))
    if session is None:
        return
    session.status = status
    if plan is not None:
        session.plan = plan
    if error_message is not None:
        session.error_message = error_message


def append_agent_event_sync(db: Session, session_id: str, event_type: str, node_name: str | None, payload: dict) -> int:
    """Insert the next event for this session, computing its sequence
    number from the current max — returns the assigned sequence number."""
    next_seq = db.execute(
        select(func.coalesce(func.max(AgentEvent.sequence), 0) + 1).where(
            AgentEvent.session_id == uuid.UUID(session_id)
        )
    ).scalar_one()

    event = AgentEvent(
        session_id=uuid.UUID(session_id),
        sequence=next_seq,
        event_type=event_type,
        node_name=node_name,
        payload=payload,
    )
    db.add(event)
    return next_seq


def save_report_sync(db: Session, session_id: str, report: dict) -> ResearchReport:
    row = ResearchReport(
        session_id=uuid.UUID(session_id),
        title=report["title"],
        summary=report["summary"],
        sections=report["sections"],
        citations=report["citations"],
        confidence_score=report["confidence_score"],
    )
    db.add(row)
    return row
