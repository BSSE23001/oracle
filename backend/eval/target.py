"""
The "system under test" for evaluation: runs the complete ORACLE agent
graph for a single query and returns the resulting report as a flat dict
that the evaluators in `eval/evaluators.py` can read fields off of
directly (`outputs["title"]`, `outputs["sections"]`, etc.).

Evaluation runs are non-interactive, so the human-in-the-loop plan-review
interrupt (`app/agents/human_review.py`) is auto-approved here rather than
prompting anyone, this evaluates the Supervisor's *first-draft* plan
quality as part of the overall report quality, which is exactly what we
want a regression-test dataset to catch (a worse plan produces a worse
report, and that should show up in the scores below).
"""

from __future__ import annotations

import logging
import uuid

from langgraph.types import Command

from app.agents.graph import build_graph
from app.agents.state import initial_state
from app.tools.vector_store import reset_session

logger = logging.getLogger("oracle.eval.target")

_MAX_REVIEW_ROUNDS = 3  # safety net, auto-approval should resolve in exactly 1 round


def run_oracle_target(inputs: dict) -> dict:
    """Signature required by `langsmith.evaluate`: takes the example's
    `inputs` dict (here just `{"query": "..."}"`) and returns the
    application's `outputs` dict."""
    query = inputs["query"]
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}

    graph = build_graph()
    result = graph.invoke(initial_state(query, session_id), config=config)

    rounds = 0
    while "__interrupt__" in result and rounds < _MAX_REVIEW_ROUNDS:
        result = graph.invoke(Command(resume={"approved": True}), config=config)
        rounds += 1

    report = result.get("report")
    try:
        reset_session(
            session_id
        )  # keep the local Chroma store from growing across eval runs
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to reset vector store session %s after eval run: %s",
            session_id,
            exc,
        )

    if report is None:
        return {
            "title": None,
            "summary": None,
            "sections": [],
            "citations": [],
            "confidence_score": 0.0,
            "error": "no_report_produced",
        }

    # report is already a plain dict (citation_formatter_node serializes
    # with .model_dump() before storing in state)
    return {**report, "error": None}
