"""Supervisor agent — decomposes the query into a ResearchPlan, and revises
that plan if the human-in-the-loop checkpoint comes back with feedback."""

from __future__ import annotations

import logging

from app.agents.prompts import PLAN_REVISION_SYSTEM, SUPERVISOR_SYSTEM
from app.agents.schemas import ResearchPlan, Subtask, SubtaskType
from app.agents.state import ResearchState
from app.config import settings
from app.core.llm import get_default_llm

logger = logging.getLogger("oracle.agents.supervisor")


def _fallback_plan(query: str) -> ResearchPlan:
    return ResearchPlan(
        objective=query,
        subtasks=[Subtask(id="t1", type=SubtaskType.WEB_SEARCH, description=query)],
    )


def supervisor_node(state: ResearchState) -> dict:
    llm = get_default_llm(temperature=0.1)
    query = state["query"]
    is_revision = bool(state.get("plan") and state.get("plan_revision_notes"))

    try:
        if is_revision:
            system = PLAN_REVISION_SYSTEM.format(
                max_subtasks=settings.max_subtasks_per_plan
            )
            previous_plan = state["plan"]
            if isinstance(previous_plan, dict):
                previous_plan = ResearchPlan.model_validate(previous_plan)
            user = (
                f"Original plan JSON:\n{previous_plan.model_dump_json(indent=2)}\n\n"
                f"User feedback: {state['plan_revision_notes']}\n\n"
                f"Original query for context: {query}"
            )
            plan = llm.generate_structured(system, user, ResearchPlan)
        else:
            system = SUPERVISOR_SYSTEM.format(
                max_subtasks=settings.max_subtasks_per_plan
            )
            plan = llm.generate_structured(
                system, f"Research query: {query}", ResearchPlan
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Plan generation failed (%s); falling back to a single web_search subtask.",
            exc,
        )
        raw = state.get("plan")
        if raw is not None:
            plan = ResearchPlan.model_validate(raw) if isinstance(raw, dict) else raw
        else:
            plan = _fallback_plan(query)

    if not plan.subtasks:
        plan.subtasks = _fallback_plan(query).subtasks

    plan.subtasks = plan.subtasks[: settings.max_subtasks_per_plan]

    # Serialize to a plain dict before storing in LangGraph state. The
    # checkpoint serializer (msgpack via PostgresSaver) doesn't know about
    # custom Pydantic classes and warns (and will hard-error in a future
    # LangGraph release) when it encounters unregistered types. Plain dicts
    # round-trip through msgpack without any registration required.
    return {
        "plan": plan.model_dump(),
        "plan_approved": False,
        "plan_revision_notes": "",
    }
