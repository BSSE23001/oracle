"""
Citation Formatter, the last node in the graph. Deduplicates every source
gathered across all specialist agents, resolves academic metadata for each
via CrossRef where possible, maps each draft section's "source_indices"
(which point at the numbered findings the synthesis agent was shown) to the
resulting citation ids, and assembles the final report dict.

State contract: `subtask_results` and `fact_check_verdicts` are lists of
plain dicts (each is the `.model_dump()` of their respective Pydantic
models). All node returns use plain dicts so the LangGraph checkpoint
serializer (msgpack) never encounters unregistered custom types.
"""

from __future__ import annotations

import logging

from app.agents.schemas import Citation, ReportSection, ResearchReport, SourceRef
from app.agents.state import ResearchState
from app.agents.utils import coerce_to_dict
from app.tools.crossref_tool import resolve_citation

logger = logging.getLogger("oracle.agents.citation_formatter")


class _CitationRegistry:
    """Tracks dedup across sources as we assign citation ids in order."""

    def __init__(self) -> None:
        self.citations: list[Citation] = []
        self._seen: dict[str, str] = {}  # dedup_key -> citation id

    def id_for(self, source: SourceRef) -> str | None:
        key = source.dedup_key()
        if not key:
            return None
        if key in self._seen:
            return self._seen[key]

        cid = f"c{len(self.citations) + 1}"
        lookup_query = source.doi or source.title or source.url
        resolved = resolve_citation(lookup_query) if lookup_query else None

        if resolved and resolved.get("title"):
            citation = Citation(
                id=cid,
                title=resolved["title"],
                authors=resolved["authors"],
                year=resolved["year"],
                venue=resolved["venue"],
                url=resolved.get("url") or source.url,
                doi=resolved.get("doi"),
            )
        else:
            citation = Citation(
                id=cid, title=source.title or source.url, url=source.url, doi=source.doi
            )

        self.citations.append(citation)
        self._seen[key] = cid
        return cid


def _compute_confidence(results: list, fact_checks: list) -> float:
    if not results:
        return 0.0

    results = [coerce_to_dict(r) for r in results]
    avg_subtask_confidence = sum(r.get("confidence", 0.5) for r in results) / len(
        results
    )

    if not fact_checks:
        return round(max(0.0, min(1.0, avg_subtask_confidence)), 2)

    fact_checks = [coerce_to_dict(f) for f in fact_checks]
    supported = sum(1 for f in fact_checks if f.get("verdict") == "supported")
    contradicted = sum(1 for f in fact_checks if f.get("verdict") == "contradicted")
    fact_check_signal = (supported - contradicted) / len(fact_checks)
    fact_check_score = (fact_check_signal + 1) / 2

    combined = 0.6 * avg_subtask_confidence + 0.4 * fact_check_score
    return round(max(0.0, min(1.0, combined)), 2)


def citation_formatter_node(state: ResearchState) -> dict:
    # Coerce each item to a plain dict, handles both new (plain dict) and
    # old (Pydantic model deserialized from a pre-fix checkpoint) formats.
    results: list[dict] = [coerce_to_dict(r) for r in state.get("subtask_results", [])]
    fact_checks: list[dict] = [
        coerce_to_dict(f) for f in state.get("fact_check_verdicts", [])
    ]

    registry = _CitationRegistry()
    finding_index_to_citation_ids: dict[int, list[str]] = {}

    for i, result in enumerate(results, start=1):
        ids: list[str] = []
        for source_data in result.get("sources", []):
            try:
                # source_data may be a plain dict (new code) or a SourceRef
                # object (old checkpoint), model_validate handles both.
                source = SourceRef.model_validate(coerce_to_dict(source_data))
                cid = registry.id_for(source)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Citation resolution failed for %r: %s", source_data, exc
                )
                cid = None
            if cid:
                ids.append(cid)
        finding_index_to_citation_ids[i] = ids

    sections: list[ReportSection] = []
    for raw_section in state.get("draft_sections", []):
        cite_ids: list[str] = []
        for idx in raw_section.get("source_indices", []):
            cite_ids.extend(finding_index_to_citation_ids.get(idx, []))
        seen_cite: set[str] = set()
        deduped = [c for c in cite_ids if not (c in seen_cite or seen_cite.add(c))]
        sections.append(
            ReportSection(
                heading=raw_section["heading"],
                content=raw_section["content"],
                citation_ids=deduped,
            )
        )

    report = ResearchReport(
        title=state.get("draft_title") or f"Research report: {state['query']}",
        summary=state.get("draft_summary", ""),
        sections=sections,
        citations=registry.citations,
        confidence_score=_compute_confidence(results, fact_checks),
    )
    # Serialize to a plain dict, keeps the checkpoint serializer happy and
    # makes the state consistent (everything is plain dicts, not Pydantic).
    return {"report": report.model_dump()}
