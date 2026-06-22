"""
Core fact-checking logic: web-search grounding + a secondary LLM call that
judges a single claim against the retrieved evidence. Used by:
  - `agents/fact_check_subtask_agent.py` (when the supervisor's plan includes
    an explicit `fact_check` subtask, e.g. the user's query itself contains
    a claim to verify)
  - `agents/fact_check_pass.py` (the automatic pass that re-checks the
    synthesized report's own key claims before the report is finalized)
"""
from __future__ import annotations

import logging
import re

from app.agents.prompts import FACT_CHECK_CLAIM_SYSTEM
from app.agents.schemas import FactCheckVerdict, SourceRef
from app.core.llm import get_default_llm
from app.tools.web_search_tool import format_hits_for_prompt, web_search

logger = logging.getLogger("oracle.agents.fact_check_logic")

_VERDICT_RE = re.compile(r"VERDICT:\s*(\w+)", re.IGNORECASE)
_VALID_VERDICTS = {"supported", "contradicted", "uncertain"}


def verify_claim(claim: str) -> FactCheckVerdict:
    hits = web_search(f"fact check: {claim}", max_results=5)
    sources_block = format_hits_for_prompt(hits)

    llm = get_default_llm(temperature=0.1)
    user = (
        f"Claim to verify: {claim}\n\n"
        f"Evidence:\n{sources_block}\n\n"
        "Respond starting with a line `VERDICT: supported` or `VERDICT: contradicted` or "
        "`VERDICT: uncertain`, followed by a short explanation referencing the evidence."
    )

    try:
        raw = llm.chat(FACT_CHECK_CLAIM_SYSTEM, user)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Fact-check LLM call failed for claim %r: %s", claim, exc)
        return FactCheckVerdict(claim=claim, verdict="uncertain", explanation=f"Fact-check failed: {exc}")

    match = _VERDICT_RE.search(raw)
    verdict = match.group(1).lower() if match else "uncertain"
    if verdict not in _VALID_VERDICTS:
        verdict = "uncertain"

    explanation = raw[match.end() :].strip() if match else raw.strip()
    sources = [SourceRef(url=h["url"], title=h["title"]) for h in hits]
    return FactCheckVerdict(claim=claim, verdict=verdict, explanation=explanation, sources=sources)
