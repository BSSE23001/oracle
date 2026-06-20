"""
Human-in-the-loop checkpoint.

This node calls LangGraph's `interrupt()`, which pauses graph execution at
exactly this point and surfaces a payload to whatever is driving the graph.
Execution resumes only when the caller invokes the graph again
with `Command(resume=<value>)`, `interrupt()` then returns `<value>` right
here, as if it had been a normal blocking function call.

This requires a checkpointer to be attached at graph-compile time (see
`agents/graph.py`), interrupts are implemented as a special checkpoint
that records "we're paused here, waiting for input."
"""

from __future__ import annotations

from langgraph.types import interrupt

from app.agents.schemas import ResearchPlan
from app.agents.state import ResearchState


def human_review_node(state: ResearchState) -> dict:
    plan = state["plan"]
    # `interrupt()` makes this node "restart from the top" on resume, and a
    # resume always re-enters via a fresh `.invoke()` call that reconstructs
    # state from the checkpoint, so this specific read is the one place in
    # the graph where a stored pydantic object could come back as a plain
    # dict instead of a `ResearchPlan`. Defend against that explicitly
    # rather than relying on it round-tripping correctly.
    if isinstance(plan, dict):
        plan = ResearchPlan.model_validate(plan)

    decision = interrupt(
        {
            "type": "plan_review",
            "plan": plan.model_dump(),
            "instructions": (
                "Review the subtasks above. Resume the graph with "
                '{"approved": true} to run the plan as-is, or '
                '{"approved": false, "feedback": "<what to change>"} to send it '
                "back to the Supervisor for revision."
            ),
        }
    )

    # `decision` is exactly whatever value the client passed to
    # Command(resume=...). Be defensive about shape since it crosses a
    # network boundary in the real API.
    if not isinstance(decision, dict):
        decision = {"approved": True}

    approved = bool(decision.get("approved", True))
    feedback = str(decision.get("feedback", "") or "")

    return {"plan_approved": approved, "plan_revision_notes": feedback}
