"""
Automatic fact-check pass over the synthesized draft.

This is distinct from `fact_check_subtask_agent.py` (which only runs when
the supervisor's plan explicitly includes a `fact_check` subtask). This
node always runs, on every research request, after synthesis: it extracts
the report's own most checkable claims and verifies each one independently
against fresh web evidence, catching synthesis hallucinations before the
report is finalized, not just trusting whatever the synthesis agent wrote.

Performance note: claim verification is done concurrently via a
ThreadPoolExecutor.  Each `verify_claim()` call involves a Tavily web
search and an LLM chat completion, which can each take tens of seconds.
Running them sequentially was a significant contributor to Celery task
timeouts.  Parallel execution caps wall-clock cost at ~one claim's latency
instead of N claims × latency.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

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

    if not claims:
        return {"fact_check_verdicts": []}

    verdicts: list[dict] = []

    # Verify all claims concurrently.  Each verify_claim() call is an
    # independent Tavily search + LLM call, so there's no shared state to
    # worry about, and running them in parallel is safe.
    def _safe_verify(claim: str) -> dict | None:
        try:
            return verify_claim(claim).model_dump()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Fact-check failed for claim %r: %s", claim, exc)
            return None

    with ThreadPoolExecutor(max_workers=_MAX_CLAIMS_TO_CHECK) as pool:
        futures = {pool.submit(_safe_verify, claim): claim for claim in claims}
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                verdicts.append(result)

    return {"fact_check_verdicts": verdicts}
