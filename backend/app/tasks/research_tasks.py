"""
The Celery tasks that actually run the agent graph.

Two entry points, mirroring the two places a research session can be
(re)started from:
  - `run_research_task`: kicks off a brand new session.
  - `resume_research_task`: resumes a session that's paused at the
    human-in-the-loop plan-review interrupt.

Both delegate to `_drive_graph`, which iterates `graph.stream(...,
stream_mode="updates")`. Each item yielded is a dict with exactly one key:
either a node name mapped to that node's return value, or the special key
"__interrupt__" mapped to a tuple of `Interrupt` objects (LangGraph's own
convention — confirmed against current LangGraph stream-mode docs). Every
item gets turned into an event that's both:
  - published to a Redis pub/sub channel (`oracle:events:{session_id}`)
    for any currently-connected SSE client to relay live, and
  - persisted to the `agent_events` table, so a client that connects (or
    reconnects) mid-run can replay everything that already happened.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from enum import Enum

import redis as redis_sync
from langgraph.types import Command

from app.config import settings
from app.db import crud
from app.db.session import SyncSessionLocal
from app.tasks.celery_app import celery_app
from app.agents.utils import coerce_to_dict

logger = logging.getLogger("oracle.tasks.research")

_redis_client: redis_sync.Redis | None = None


def _get_redis() -> redis_sync.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_sync.Redis.from_url(
            settings.redis_url, decode_responses=True
        )
    return _redis_client


def _json_safe(value):
    """Recursively convert pydantic models / Enums into plain JSON-safe
    structures before they go into Redis or a JSONB column."""
    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump())
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def _publish_event(
    session_id: str, event_type: str, node_name: str | None, data
) -> None:
    safe_data = _json_safe(data)
    with SyncSessionLocal() as db:
        sequence = crud.append_agent_event_sync(
            db, session_id, event_type, node_name, safe_data
        )
        db.commit()

    message = json.dumps(
        {
            "type": event_type,
            "node": node_name,
            "data": safe_data,
            "sequence": sequence,
            "ts": datetime.now(timezone.utc).isoformat(),
        },
        default=str,
    )
    try:
        _get_redis().publish(f"oracle:events:{session_id}", message)
    except (
        Exception
    ) as exc:  # noqa: BLE001 - a Redis hiccup should never lose the Postgres-persisted event
        logger.warning(
            "Failed to publish live event for session %s: %s", session_id, exc
        )


_SPECIALIST_NODES = frozenset(
    {"web_search_agent", "pdf_agent", "code_exec_agent", "fact_check_subtask_agent"}
)


def _drive_graph(graph, graph_input, config: dict, session_id: str) -> None:
    """
    Drive the graph to completion (or to the next interrupt), publishing
    every node update as an event.
    """
    interrupt_payload = None
    stream = graph.stream(graph_input, config=config, stream_mode="updates")
    try:
        for chunk in stream:
            if "__interrupt__" in chunk:
                interrupt_payload = chunk["__interrupt__"][0].value
                break  # break cleanly; finally block closes the stream
            for node_name, update in chunk.items():
                if node_name in _SPECIALIST_NODES:
                    for r in update.get("subtask_results") or []:
                        r = coerce_to_dict(
                            r
                        )  # handles both dict (new) and SubtaskResult object (old checkpoint)
                        logger.info(
                            "[PARALLEL] Agent %-28s done — subtask %s, confidence %.0f%%",
                            node_name,
                            r.get("subtask_id", "?"),
                            r.get("confidence", 0) * 100,
                        )
                _publish_event(session_id, "node_update", node_name, update)
    finally:
        stream.close()  # always close explicitly, prevents GeneratorExit from surfacing as an error

    if interrupt_payload is not None:
        with SyncSessionLocal() as db:
            crud.update_session_status_sync(
                db, session_id, "awaiting_review", plan=interrupt_payload.get("plan")
            )
            db.commit()
        _publish_event(
            session_id, "plan_review_required", "human_review", interrupt_payload
        )
        return

    # Stream ended without another interrupt → the graph reached END.
    state_snapshot = graph.get_state(config)
    report = state_snapshot.values.get("report") if state_snapshot else None

    if report is None:
        with SyncSessionLocal() as db:
            crud.update_session_status_sync(
                db,
                session_id,
                "failed",
                error_message="Graph completed without producing a report.",
            )
            db.commit()
        _publish_event(
            session_id, "session_failed", None, {"error": "no report produced"}
        )
        return

    report_dict = _json_safe(report)
    with SyncSessionLocal() as db:
        crud.save_report_sync(db, session_id, report_dict)
        crud.update_session_status_sync(db, session_id, "completed")
        db.commit()
    _publish_event(session_id, "session_completed", "citation_formatter", report_dict)


def _fail_session(session_id: str, exc: Exception) -> None:
    logger.exception("Research task failed for session %s", session_id)
    with SyncSessionLocal() as db:
        crud.update_session_status_sync(
            db, session_id, "failed", error_message=str(exc)
        )
        db.commit()
    _publish_event(session_id, "session_failed", None, {"error": str(exc)})


@celery_app.task(name="oracle.run_research", bind=True)
def run_research_task(self, session_id: str, query: str) -> None:
    # `get_process_graph` is imported lazily here (same as before) so that
    # the Postgres checkpointer isn't initialised when the FastAPI *api*
    # container imports this module — only the *worker* container ever
    # executes this function.
    from app.agents.graph import get_process_graph  # noqa: PLC0415
    from app.agents.state import initial_state  # noqa: PLC0415

    with SyncSessionLocal() as db:
        crud.update_session_status_sync(db, session_id, "planning")
        db.commit()
    _publish_event(session_id, "session_started", None, {"query": query})

    config = {"configurable": {"thread_id": session_id}}
    try:
        graph = get_process_graph()
        _drive_graph(graph, initial_state(query, session_id), config, session_id)
    except Exception as exc:  # noqa: BLE001
        _fail_session(session_id, exc)


@celery_app.task(name="oracle.resume_research", bind=True)
def resume_research_task(self, session_id: str, decision: dict) -> None:
    from app.agents.graph import get_process_graph  # noqa: PLC0415

    with SyncSessionLocal() as db:
        crud.update_session_status_sync(db, session_id, "running")
        db.commit()
    _publish_event(session_id, "plan_decision_received", "human_review", decision)

    config = {"configurable": {"thread_id": session_id}}
    try:
        # MUST use get_process_graph() here, NOT build_graph(), so this
        # task shares the same PostgresSaver connection as the
        # run_research_task that originally wrote the paused checkpoint.
        # build_graph() would create a fresh connection, which would read
        # from Postgres fine (the checkpoint is stored there), but a fresh
        # build also re-initialises the checkpointer tables (setup()), and
        # in some versions of langgraph-checkpoint-postgres that is a
        # no-op only if the tables already exist, safe but wasteful. More
        # importantly it's a second open connection for no reason.
        graph = get_process_graph()
        _drive_graph(graph, Command(resume=decision), config, session_id)
    except Exception as exc:  # noqa: BLE001
        _fail_session(session_id, exc)
