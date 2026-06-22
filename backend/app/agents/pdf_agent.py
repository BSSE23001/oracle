"""PDF Reader specialist agent, reads a specific document (URL or local
path given in the subtask's input_data) and extracts what's relevant.

Graceful degradation: if the supervisor created a pdf_reader subtask
without actually knowing a document URL (input_data empty), this falls
back to a web search for the subtask description instead of failing
outright, that keeps a planning mistake from sinking the whole run.
"""

from __future__ import annotations

import logging

from app.agents.prompts import PDF_AGENT_SYSTEM, WEB_SEARCH_AGENT_SYSTEM
from app.agents.schemas import Subtask, SourceRef, SubtaskResult
from app.agents.utils import parse_confidence_suffix
from app.core.llm import get_default_llm
from app.tools.pdf_tools import format_for_prompt, read_pdf
from app.tools.vector_store import ingest_document
from app.tools.web_search_tool import format_hits_for_prompt, web_search

logger = logging.getLogger("oracle.agents.pdf")


def pdf_agent(payload: dict) -> dict:
    subtask = Subtask.model_validate(payload["subtask"])
    session_id: str = payload["session_id"]
    source = subtask.input_data.strip()

    if not source:
        logger.info(
            "pdf_reader subtask %s had no document URL; falling back to web search.",
            subtask.id,
        )
        hits = web_search(subtask.description, max_results=5)
        sources_block = format_hits_for_prompt(hits)
        llm = get_default_llm(temperature=0.2)
        try:
            raw = llm.chat(
                WEB_SEARCH_AGENT_SYSTEM,
                f"Subtask: {subtask.description}\n\nSources:\n{sources_block}",
            )
            summary, confidence = parse_confidence_suffix(raw)
        except Exception as exc:  # noqa: BLE001
            summary, confidence = (
                f"No document was specified and the web-search fallback failed: {exc}",
                0.0,
            )
        sources = [SourceRef(url=h["url"], title=h["title"]) for h in hits]
        result = SubtaskResult(
            subtask_id=subtask.id,
            subtask_type=subtask.type,
            summary=f"(No document URL was provided for this subtask — used a web search instead.) {summary}",
            sources=sources,
            confidence=confidence
            * 0.8,  # slightly discount confidence since this wasn't the intended path
        )
        return {"subtask_results": [result]}

    pdf_result = read_pdf(source)
    if pdf_result.error:
        result = SubtaskResult(
            subtask_id=subtask.id,
            subtask_type=subtask.type,
            summary=f"Could not read the document at {source}: {pdf_result.error}",
            confidence=0.0,
            error=pdf_result.error,
        )
        return {"subtask_results": [result]}

    ingest_document(
        session_id,
        source,
        pdf_result.full_text,
        extra_metadata={"subtask_id": subtask.id},
    )

    document_block = format_for_prompt(pdf_result)
    llm = get_default_llm(temperature=0.2)
    user = f"Subtask: {subtask.description}\n\nDocument content:\n{document_block}"
    try:
        raw = llm.chat(PDF_AGENT_SYSTEM, user)
        summary, confidence = parse_confidence_suffix(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "pdf_agent summarization failed for subtask %s: %s", subtask.id, exc
        )
        summary, confidence = "Document was read but could not be summarized.", 0.1

    result = SubtaskResult(
        subtask_id=subtask.id,
        subtask_type=subtask.type,
        summary=summary,
        sources=[SourceRef(url=source, title=source.rsplit("/", 1)[-1])],
        confidence=confidence,
        raw_excerpt=document_block[:1500],
    )
    return {"subtask_results": [result]}
