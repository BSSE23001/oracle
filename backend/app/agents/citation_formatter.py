"""
Citation Formatter, the last node in the graph. Deduplicates every source
gathered across all specialist agents, resolves academic metadata for each
via CrossRef where possible, maps each draft section's "source_indices"
(which point at the numbered findings the synthesis agent was shown) to the
resulting citation ids, and assembles the final `ResearchReport`.

Also computes the report's overall `confidence_score`, a blend of how
confident each specialist agent was in its own findings and how the
post-synthesis fact-check pass came out.
"""

from __future__ import annotations

import logging

from app.agents.schemas import (
    Citation,
    FactCheckVerdict,
    ReportSection,
    ResearchReport,
    SourceRef,
    SubtaskResult,
)
from app.agents.state import ResearchState
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


def _compute_confidence(
    results: list[SubtaskResult], fact_checks: list[FactCheckVerdict]
) -> float:
    if not results:
        return 0.0

    avg_subtask_confidence = sum(r.confidence for r in results) / len(results)

    if not fact_checks:
        return round(max(0.0, min(1.0, avg_subtask_confidence)), 2)

    supported = sum(1 for f in fact_checks if f.verdict == "supported")
    contradicted = sum(1 for f in fact_checks if f.verdict == "contradicted")
    fact_check_signal = (supported - contradicted) / len(fact_checks)  # in [-1, 1]
    fact_check_score = (fact_check_signal + 1) / 2  # normalize to [0, 1]

    combined = 0.6 * avg_subtask_confidence + 0.4 * fact_check_score
    return round(max(0.0, min(1.0, combined)), 2)


def citation_formatter_node(state: ResearchState) -> dict:
    results: list[SubtaskResult] = state.get("subtask_results", [])
    fact_checks: list[FactCheckVerdict] = state.get("fact_check_verdicts", [])

    registry = _CitationRegistry()
    finding_index_to_citation_ids: dict[int, list[str]] = {}

    for i, result in enumerate(results, start=1):
        ids: list[str] = []
        for source in result.sources:
            try:
                cid = registry.id_for(source)
            except (
                Exception
            ) as exc:  # noqa: BLE001 - CrossRef hiccups must never break report assembly
                logger.warning("Citation resolution failed for %r: %s", source, exc)
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
    return {"report": report}
