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

Performance note: CrossRef resolution is done concurrently via a
ThreadPoolExecutor.  Sequential resolution against CrossRef's API (each
call up to 15 s) was the primary cause of the Celery task exceeding the
900-second hard time limit.  Resolving N sources in parallel caps the
wall-clock cost at ~one round-trip instead of N round-trips.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.agents.schemas import Citation, ReportSection, ResearchReport, SourceRef
from app.agents.state import ResearchState
from app.agents.utils import coerce_to_dict
from app.tools.crossref_tool import resolve_citation

logger = logging.getLogger("oracle.agents.citation_formatter")

# Maximum parallel CrossRef lookups. CrossRef's polite-pool rate limit is
# generous (~50 req/s), so 8 concurrent connections is safe and dramatically
# reduces wall-clock time vs. sequential calls.
_CROSSREF_WORKERS = 8


def _is_web_url(query: str) -> bool:
    """Return True for plain web URLs that CrossRef cannot resolve.

    CrossRef only knows about academic DOIs and paper titles.  Sending it a
    general web URL (https://…) is always a wasted HTTP round-trip, so we
    skip those lookups entirely.
    """
    q = query.lower().strip()
    return q.startswith("http://") or q.startswith("https://")


class _CitationRegistry:
    """Tracks dedup across sources as we assign citation ids in order."""

    def __init__(self) -> None:
        self.citations: list[Citation] = []
        self._seen: dict[str, str] = {}  # dedup_key -> citation id
        # Pre-collected (source, lookup_query) pairs waiting for resolution.
        self._pending: list[tuple[SourceRef, str | None]] = []

    def collect(self, source: SourceRef) -> str | None:
        """Register a source and return its (possibly pre-existing) citation id.

        Returns None if the source has no dedup key (and therefore won't be
        cited), or the *existing* id if already seen.  New sources are added
        to `_pending` so they can be resolved in bulk via `resolve_all()`.
        """
        key = source.dedup_key()
        if not key:
            return None
        if key in self._seen:
            return self._seen[key]

        # Reserve an id now so ordering is stable even though resolution
        # happens in parallel later.
        cid = f"c{len(self.citations) + 1}"
        # Placeholder — will be replaced after resolution.
        self.citations.append(Citation(id=cid, title=source.title or source.url, url=source.url, doi=source.doi))
        self._seen[key] = cid
        lookup_query = source.doi or source.title or source.url
        self._pending.append((source, lookup_query, cid))  # type: ignore[arg-type]
        return cid

    def resolve_all(self) -> None:
        """Resolve all pending CrossRef lookups concurrently and patch citations in-place."""
        if not self._pending:
            return

        def _resolve(args: tuple) -> tuple[str, dict | None]:
            source, lookup_query, cid = args
            if not lookup_query:
                return cid, None
            # Skip CrossRef for plain web URLs with no DOI.
            # CrossRef only indexes academic papers; querying it for a Wikipedia
            # article / news post / blog is a guaranteed miss that wastes one HTTP
            # round-trip per source and was causing "read operation timed out"
            # warnings in the logs even at 5-second timeout.
            # We keep CrossRef for: (a) DOIs, (b) sources whose URL is absent
            # (e.g. PDF agent found an academic reference without a URL).
            has_doi = bool(source.doi)
            has_web_url = _is_web_url(source.url or "")
            if not has_doi and has_web_url:
                return cid, None
            # Also skip if lookup_query itself is a web URL (title fell back to URL).
            if not has_doi and _is_web_url(lookup_query):
                return cid, None
            try:
                return cid, resolve_citation(lookup_query)
            except Exception as exc:  # noqa: BLE001
                logger.warning("CrossRef resolution failed for %r: %s", lookup_query, exc)
                return cid, None

        # Build an id→index map so we can update in-place.
        id_to_index = {c.id: i for i, c in enumerate(self.citations)}

        with ThreadPoolExecutor(max_workers=_CROSSREF_WORKERS) as pool:
            futures = {pool.submit(_resolve, args): args for args in self._pending}
            for future in as_completed(futures):
                try:
                    cid, resolved = future.result()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Citation resolution future failed: %s", exc)
                    continue

                if not resolved or not resolved.get("title"):
                    continue  # keep the placeholder built in collect()

                idx = id_to_index.get(cid)
                if idx is None:
                    continue

                # Find the original source to fall back to its URL.
                args = futures[future]
                source = args[0]
                self.citations[idx] = Citation(
                    id=cid,
                    title=resolved["title"],
                    authors=resolved.get("authors", []),
                    year=resolved.get("year"),
                    venue=resolved.get("venue"),
                    url=resolved.get("url") or source.url,
                    doi=resolved.get("doi"),
                )


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

    # Pass 1 — register every source and assign placeholder citation ids.
    for i, result in enumerate(results, start=1):
        ids: list[str] = []
        for source_data in result.get("sources", []):
            try:
                # source_data may be a plain dict (new code) or a SourceRef
                # object (old checkpoint), model_validate handles both.
                source = SourceRef.model_validate(coerce_to_dict(source_data))
                cid = registry.collect(source)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Citation collection failed for %r: %s", source_data, exc
                )
                cid = None
            if cid:
                ids.append(cid)
        finding_index_to_citation_ids[i] = ids

    # Pass 2 — resolve all CrossRef lookups concurrently (the expensive step).
    registry.resolve_all()

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
