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
from app.agents.state import ResearchState
from app.agents.utils import coerce_to_dict
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


def _build_findings_block(results: list) -> str:
    if not results:
        return "(no findings were gathered)"
    lines = []
    for i, raw in enumerate(results, start=1):
        r = coerce_to_dict(
            raw
        )  # handles SubtaskResult objects (old checkpoints) and plain dicts (new code)
        subtask_id = r.get("subtask_id", "?")
        subtask_type = r.get("subtask_type", "unknown")
        confidence = r.get("confidence", 0.0)
        summary = r.get("summary", "")
        lines.append(
            f"Finding [{i}] (subtask {subtask_id}, type={subtask_type}, "
            f"confidence={confidence:.2f}):\n{summary}\n"
        )
    return "\n".join(lines)


def synthesis_agent(state: ResearchState) -> dict:
    results: list = state.get(
        "subtask_results", []
    )  # may be dicts (new) or SubtaskResult objects (old checkpoint)
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
