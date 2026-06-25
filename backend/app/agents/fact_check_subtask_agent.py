"""Fact-Check specialist agent, handles explicit `fact_check` subtasks the
supervisor created because the user's query itself contained a claim to
verify. (The separate automatic fact-check pass over the synthesized
report's own claims lives in `fact_check_pass.py` and shares the same
underlying `verify_claim()` logic from `fact_check_logic.py`.)"""

from __future__ import annotations

import logging

from app.agents.fact_check_logic import verify_claim
from app.agents.schemas import Subtask, SubtaskResult

logger = logging.getLogger("oracle.agents.fact_check_subtask")

_CONFIDENCE_BY_VERDICT = {"supported": 0.85, "contradicted": 0.85, "uncertain": 0.3}


def fact_check_subtask_agent(payload: dict) -> dict:
    subtask = Subtask.model_validate(payload["subtask"])
    claim = subtask.input_data.strip() or subtask.description

    verdict = verify_claim(claim)
    confidence = _CONFIDENCE_BY_VERDICT.get(verdict.verdict, 0.3)
    summary = f"Verdict: {verdict.verdict}. {verdict.explanation}"

    result = SubtaskResult(
        subtask_id=subtask.id,
        subtask_type=subtask.type,
        summary=summary,
        sources=verdict.sources,
        confidence=confidence,
    )
    return {"subtask_results": [result.model_dump()]}
