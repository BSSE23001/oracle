"""Synthesis agent, the fan-in point after every specialist agent has
returned. Combines their findings into a structured draft (title, summary,
sections), each section pointing back at which numbered findings support
it. Citation resolution happens later in `citation_formatter.py`; this
node only deals with content and the lightweight 1-based "finding index"
references the prompt asks for.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from app.agents.prompts import SYNTHESIS_SYSTEM
from app.agents.schemas import SubtaskResult
from app.agents.state import ResearchState
from app.core.llm import get_default_llm

logger = logging.getLogger("oracle.agents.synthesis")


class _SynthesisSection(BaseModel):
    heading: str
    content: str
    source_indices: list[int] = Field(default_factory=list)


class _SynthesisOutput(BaseModel):
    title: str
    summary: str
    sections: list[_SynthesisSection]


def _build_findings_block(results: list[SubtaskResult]) -> str:
    if not results:
        return "(no findings were gathered)"
    lines = []
    for i, r in enumerate(results, start=1):
        lines.append(
            f"Finding [{i}] (subtask {r.subtask_id}, type={r.subtask_type.value}, "
            f"confidence={r.confidence:.2f}):\n{r.summary}\n"
        )
    return "\n".join(lines)


def synthesis_agent(state: ResearchState) -> dict:
    results: list[SubtaskResult] = state.get("subtask_results", [])
    query = state["query"]
    findings_block = _build_findings_block(results)

    llm = get_default_llm(temperature=0.3)
    user = f"Original research query: {query}\n\nFindings:\n{findings_block}"

    try:
        draft = llm.generate_structured(SYNTHESIS_SYSTEM, user, _SynthesisOutput)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Synthesis failed (%s); falling back to a raw-findings dump.", exc
        )
        draft = _SynthesisOutput(
            title=f"Research notes: {query}",
            summary="Automatic synthesis failed; raw findings from each agent are included below.",
            sections=[
                _SynthesisSection(
                    heading="Raw findings",
                    content=findings_block,
                    source_indices=list(range(1, len(results) + 1)),
                )
            ],
        )

    return {
        "draft_title": draft.title,
        "draft_summary": draft.summary,
        "draft_sections": [s.model_dump() for s in draft.sections],
    }
