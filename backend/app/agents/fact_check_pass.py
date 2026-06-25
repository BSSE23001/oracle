"""
Automatic fact-check pass over the synthesized draft.

This is distinct from `fact_check_subtask_agent.py` (which only runs when
the supervisor's plan explicitly includes a `fact_check` subtask). This
node always runs, on every research request, after synthesis: it extracts
the report's own most checkable claims and verifies each one independently
against fresh web evidence, catching synthesis hallucinations before the
report is finalized, not just trusting whatever the synthesis agent wrote.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from app.agents.fact_check_logic import verify_claim
from app.agents.prompts import EXTRACT_CLAIMS_SYSTEM
from app.agents.state import ResearchState
from app.core.llm import get_default_llm

logger = logging.getLogger("oracle.agents.fact_check_pass")

_MAX_CLAIMS_TO_CHECK = 5


class _ClaimList(BaseModel):
    claims: list[str]


def fact_check_pass_node(state: ResearchState) -> dict:
    sections = state.get("draft_sections", [])
    draft_text = "\n\n".join(f"{s['heading']}\n{s['content']}" for s in sections)

    if not draft_text.strip():
        return {"fact_check_verdicts": []}

    llm = get_default_llm(temperature=0.0)
    try:
        claim_list = llm.generate_structured(
            EXTRACT_CLAIMS_SYSTEM, draft_text, _ClaimList
        )
        claims = claim_list.claims[:_MAX_CLAIMS_TO_CHECK]
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Claim extraction failed (%s); skipping the fact-check pass.", exc
        )
        return {"fact_check_verdicts": []}

    verdicts = []
    for claim in claims:
        try:
            verdicts.append(verify_claim(claim).model_dump())
        except Exception as exc:  # noqa: BLE001
            logger.warning("Fact-check failed for claim %r: %s", claim, exc)

    return {"fact_check_verdicts": verdicts}
