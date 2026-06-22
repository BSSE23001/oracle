"""
The ORACLE agent graph.

    START
      |
      v
  supervisor  <---------------------------------------------+
      |                                                      |
      v                                                      |
  human_review --[not approved, feedback given]--------------+
      |
      | [approved] -- fan out via Send(), one per subtask --
      |
      +--> web_search_agent --------+
      +--> pdf_agent ----------------+--> synthesis_agent --> fact_check_pass --> citation_formatter --> END
      +--> code_exec_agent ----------+
      +--> fact_check_subtask_agent -+

`human_review` is where the real LangGraph human-in-the-loop feature lives:
it calls `interrupt()`, which pauses execution and persists the paused
state via the checkpointer. The caller (FastAPI endpoint / Celery task)
resumes it with `Command(resume={...})`.

## Checkpointer design

We use `psycopg.connect()` directly rather than `PostgresSaver.from_conn_string()`
context manager because the context manager pattern is NOT safe here:
`from_conn_string()` returns a `_GeneratorContextManager`; manually calling
`.__enter__()` on it pauses the generator (and keeps the psycopg connection
open) only as long as the local variable `saver_cm` exists. The moment
`get_default_checkpointer()` returns, `saver_cm` goes out of scope, Python's
reference-counting GC destroys it, which closes the underlying psycopg
connection — and the returned `saver` now wraps a dead connection. Using
`psycopg.connect()` directly gives us a connection whose lifetime is
controlled by our own references, not the GC.

## Process-level graph cache

`get_process_graph()` caches one compiled graph per worker process.
The Celery worker runs `run_research_task` (builds the graph, drives it to
the interrupt), then later runs `resume_research_task` (must resume the same
LangGraph thread). Both tasks must use the same checkpointer instance, not
because LangGraph requires it, but because a Postgres checkpointer wraps a
single connection: if `run_research_task` closes its connection before
`resume_research_task` calls `graph.stream(Command(resume=...))`, the
resume will have nothing to read the paused state through. Caching the graph
at the process level keeps the connection alive for the process lifetime.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from pathlib import Path
from typing import Optional

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send

from app.agents.citation_formatter import citation_formatter_node
from app.agents.code_exec_agent import code_exec_agent
from app.agents.fact_check_pass import fact_check_pass_node
from app.agents.fact_check_subtask_agent import fact_check_subtask_agent
from app.agents.human_review import human_review_node
from app.agents.pdf_agent import pdf_agent
from app.agents.schemas import ResearchPlan, SubtaskType
from app.agents.state import ResearchState
from app.agents.supervisor import supervisor_node
from app.agents.synthesis_agent import synthesis_agent
from app.agents.web_search_agent import web_search_agent
from app.config import settings

logger = logging.getLogger("oracle.agents.graph")

_NODE_FOR_SUBTASK_TYPE = {
    SubtaskType.WEB_SEARCH: "web_search_agent",
    SubtaskType.PDF_READER: "pdf_agent",
    SubtaskType.CODE_EXEC: "code_exec_agent",
    SubtaskType.FACT_CHECK: "fact_check_subtask_agent",
}
_SPECIALIST_NODES = (
    "web_search_agent",
    "pdf_agent",
    "code_exec_agent",
    "fact_check_subtask_agent",
)

# ── Process-level graph cache ────────────────────────────────────────────
# One graph instance per worker process.  A threading.Lock guards against
# the (unlikely but possible) case of two Celery tasks spawning in the same
# process before the first one has finished building the graph.
_process_graph: Optional[CompiledStateGraph] = None
_process_graph_lock = threading.Lock()


def _route_after_human_review(state: ResearchState) -> str | list[Send]:
    """
    Conditional edge out of human_review.
    - Not approved → loop back to "supervisor".
    - Approved → fan out to every subtask's specialist agent in parallel
      via Send().
    """
    if not state.get("plan_approved"):
        return "supervisor"

    plan = state["plan"]
    if isinstance(plan, dict):
        plan = ResearchPlan.model_validate(plan)
    return [
        Send(
            _NODE_FOR_SUBTASK_TYPE[subtask.type],
            {"subtask": subtask.model_dump(), "session_id": state["session_id"]},
        )
        for subtask in plan.subtasks
    ]


def build_graph(checkpointer: BaseCheckpointSaver | None = None) -> CompiledStateGraph:
    """Build and compile the StateGraph.  Pass an explicit `checkpointer` to
    override the default (useful in tests, pass `InMemorySaver()`).
    For normal runtime use `get_process_graph()` instead, which caches."""
    builder = StateGraph(ResearchState)

    builder.add_node("supervisor", supervisor_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("web_search_agent", web_search_agent)
    builder.add_node("pdf_agent", pdf_agent)
    builder.add_node("code_exec_agent", code_exec_agent)
    builder.add_node("fact_check_subtask_agent", fact_check_subtask_agent)
    builder.add_node("synthesis_agent", synthesis_agent)
    builder.add_node("fact_check_pass", fact_check_pass_node)
    builder.add_node("citation_formatter", citation_formatter_node)

    builder.add_edge(START, "supervisor")
    builder.add_edge("supervisor", "human_review")
    builder.add_conditional_edges("human_review", _route_after_human_review)

    for node_name in _SPECIALIST_NODES:
        builder.add_edge(node_name, "synthesis_agent")

    builder.add_edge("synthesis_agent", "fact_check_pass")
    builder.add_edge("fact_check_pass", "citation_formatter")
    builder.add_edge("citation_formatter", END)

    return builder.compile(
        checkpointer=checkpointer if checkpointer is not None else _make_checkpointer()
    )


def get_process_graph() -> CompiledStateGraph:
    """Return the process-level cached compiled graph, building it on the
    first call.  All Celery tasks in the same worker process share this
    single graph, and thus the same checkpointer connection, which is
    what lets `resume_research_task` pick up a thread left paused by
    `run_research_task` without opening a second database connection."""
    global _process_graph
    if _process_graph is not None:
        return _process_graph
    with _process_graph_lock:
        if _process_graph is None:
            _process_graph = build_graph()
    return _process_graph


def _make_checkpointer() -> BaseCheckpointSaver:
    """
    Create a fresh checkpointer backed by the configured storage engine.

    Postgres path: uses `psycopg.connect()` DIRECTLY, NOT via the
    `PostgresSaver.from_conn_string()` context manager. The context manager
    pattern is broken for long-lived use: `from_conn_string()` returns a
    `_GeneratorContextManager`; manually calling `.__enter__()` yields the
    saver but keeps the generator paused, and once the caller's stack frame
    exits, the `_GeneratorContextManager` local variable is GC-collected,
    which closes the underlying psycopg connection and leaves the saver
    wrapping a dead connection.  Using `psycopg.connect()` directly avoids
    this entirely, the connection lives as long as the `PostgresSaver`
    object does.

    SQLite path: `sqlite3.connect(..., check_same_thread=False)` + direct
    `SqliteSaver(conn)` constructor, no context manager involved.
    """
    if settings.checkpointer_backend == "postgres":
        try:
            import psycopg
            from langgraph.checkpoint.postgres import PostgresSaver
        except ImportError as exc:
            raise RuntimeError(
                "CHECKPOINTER_BACKEND=postgres requires 'psycopg[binary]' and "
                "'langgraph-checkpoint-postgres' to be installed. "
                "Run: pip install 'psycopg[binary]' langgraph-checkpoint-postgres"
            ) from exc

        conn_string = settings.database_url_psycopg_raw
        logger.info(
            "Connecting checkpointer to Postgres: %s", conn_string.split("@")[-1]
        )  # log host only, not creds
        conn = psycopg.connect(conn_string, autocommit=True)
        saver = PostgresSaver(conn)
        saver.setup()
        logger.info("PostgresSaver ready.")
        return saver

    # SQLite — local dev / run_local.py
    from langgraph.checkpoint.sqlite import SqliteSaver

    db_path = Path(settings.checkpointer_sqlite_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    saver = SqliteSaver(conn)
    logger.info("SqliteSaver ready at %s", db_path)
    return saver


# Keep the old public name for backwards-compat with run_local.py and tests.
get_default_checkpointer = _make_checkpointer
