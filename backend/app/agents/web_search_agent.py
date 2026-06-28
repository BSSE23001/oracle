"""Web Search specialist agent, runs Tavily, ingests hits into the session's
vector store for later RAG, and summarizes the relevant findings."""

from __future__ import annotations

import logging

from app.agents.prompts import WEB_SEARCH_AGENT_SYSTEM
from app.agents.schemas import SourceRef, Subtask, SubtaskResult
from app.agents.utils import parse_confidence_suffix
from app.core.llm import get_default_llm
from app.tools.vector_store import ingest_document
from app.tools.web_search_tool import format_hits_for_prompt, web_search

logger = logging.getLogger("oracle.agents.web_search")


def web_search_agent(payload: dict) -> dict:
    """
    `payload` is the dict a `Send("web_search_agent", payload)` call carries
    (see `route_to_specialists` in graph.py), NOT the full graph state.
    Expected keys: "subtask" (Subtask), "session_id" (str).
    """
    subtask = Subtask.model_validate(payload["subtask"])
    session_id: str = payload["session_id"]
    search_query = subtask.input_data.strip() or subtask.description

    hits = web_search(search_query, max_results=5)
    if not hits:
        result = SubtaskResult(
            subtask_id=subtask.id,
            subtask_type=subtask.type,
            summary="No web search results were found for this subtask.",
            confidence=0.0,
            error="empty_search_results",
        )
        return {
            "subtask_results": [result.model_dump()]
        }  # must match every other return path

    for hit in hits:
        if hit.get("content"):
            ingest_document(
                session_id,
                hit["url"],
                hit["content"],
                extra_metadata={"subtask_id": subtask.id},
            )

    sources_block = format_hits_for_prompt(hits)
    llm = get_default_llm(temperature=0.2)
    user = f"Subtask: {subtask.description}\n\nSources:\n{sources_block}"

    try:
        raw = llm.chat(WEB_SEARCH_AGENT_SYSTEM, user)
        summary, confidence = parse_confidence_suffix(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "web_search_agent summarization failed for subtask %s: %s", subtask.id, exc
        )
        summary, confidence = "Search succeeded but summarization failed.", 0.1

    sources = [SourceRef(url=h["url"], title=h["title"]) for h in hits]
    result = SubtaskResult(
        subtask_id=subtask.id,
        subtask_type=subtask.type,
        summary=summary,
        sources=sources,
        confidence=confidence,
        raw_excerpt=sources_block[:1500],
    )
    return {"subtask_results": [result.model_dump()]}
