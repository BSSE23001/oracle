"""
The graph-level state. Every node receives (a view of) this and returns a
partial dict; LangGraph merges partial updates back in using the reducer
attached to each `Annotated` field below.

`subtask_results` and `fact_check_verdicts` use `operator.add` because
multiple specialist agents run in parallel (via `Send`, see
`agents/graph.py`) and each contributes one item to the list, LangGraph
concatenates those contributions across the parallel branches rather than
the default "last write wins" behaviour, which is what lets four agents
run concurrently without clobbering each other's results.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from app.agents.schemas import (
    FactCheckVerdict,
    ResearchPlan,
    ResearchReport,
    SubtaskResult,
)


class ResearchState(TypedDict, total=False):
    # ── Input ────────────────────────────────────────────────────────────
    query: str
    session_id: str

    # ── Supervisor / human-in-the-loop ──────────────────────────────────
    plan: ResearchPlan
    plan_approved: bool
    plan_revision_notes: (
        str  # free-text edits the user supplied at the review checkpoint
    )

    # ── Specialist agent fan-out results ────────────────────────────────
    subtask_results: Annotated[list[SubtaskResult], operator.add]

    # ── Synthesis ────────────────────────────────────────────────────────
    draft_title: str
    draft_summary: str
    draft_sections: list[
        dict
    ]  # [{"heading": str, "content": str, "source_indices": [int, ...]}]

    # ── Fact-checking pass over the synthesized draft ───────────────────
    fact_check_verdicts: Annotated[list[FactCheckVerdict], operator.add]

    # ── Final output ─────────────────────────────────────────────────────
    report: ResearchReport

    # ── Diagnostics ──────────────────────────────────────────────────────
    error_log: Annotated[list[str], operator.add]


def initial_state(query: str, session_id: str) -> ResearchState:
    """Build a fully-initialized state dict for graph.invoke()/.stream(),
    explicitly seeding the reducer-backed list fields avoids KeyErrors in
    node code that reads them before anything has appended to them."""
    return ResearchState(
        query=query,
        session_id=session_id,
        plan_approved=False,
        plan_revision_notes="",
        subtask_results=[],
        fact_check_verdicts=[],
        error_log=[],
    )
