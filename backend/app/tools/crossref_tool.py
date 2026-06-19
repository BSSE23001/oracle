"""
CrossRef tool: free, keyless metadata lookup for academic citations.

CrossRef rewards including a contact email in the User-Agent with access to
their faster "polite pool" (see https://api.crossref.org/swagger-ui/index.html),
so we attach CROSSREF_MAILTO when set. The API still works without it.
"""

from __future__ import annotations

import logging
from typing import TypedDict

import httpx

from app.config import settings

logger = logging.getLogger("oracle.tools.crossref")

CROSSREF_BASE = "https://api.crossref.org"


class CitationMetadata(TypedDict):
    title: str | None
    authors: list[str]
    year: int | None
    venue: str | None
    doi: str | None
    url: str | None


def _headers() -> dict[str, str]:
    ua = "ORACLE-Research-Assistant/1.0 (https://github.com/; mailto:%s)" % (
        settings.crossref_mailto or "no-contact-provided@example.com"
    )
    return {"User-Agent": ua}


def _parse_item(item: dict) -> CitationMetadata:
    title = (item.get("title") or [None])[0]

    authors: list[str] = []
    for author in item.get("author", []) or []:
        name = f"{author.get('given', '')} {author.get('family', '')}".strip()
        if name:
            authors.append(name)

    year = None
    date_block = (
        item.get("published-print")
        or item.get("published-online")
        or item.get("issued")
        or {}
    )
    date_parts = date_block.get("date-parts")
    if date_parts and date_parts[0]:
        year = date_parts[0][0]

    venue = (item.get("container-title") or [None])[0]

    return CitationMetadata(
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        doi=item.get("DOI"),
        url=item.get("URL"),
    )


def lookup_by_doi(doi: str) -> CitationMetadata | None:
    try:
        resp = httpx.get(
            f"{CROSSREF_BASE}/works/{doi}", headers=_headers(), timeout=15.0
        )
        resp.raise_for_status()
        return _parse_item(resp.json()["message"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("CrossRef DOI lookup failed for %r: %s", doi, exc)
        return None


def search_by_title(title: str, rows: int = 1) -> list[CitationMetadata]:
    try:
        resp = httpx.get(
            f"{CROSSREF_BASE}/works",
            params={"query.bibliographic": title, "rows": rows},
            headers=_headers(),
            timeout=15.0,
        )
        resp.raise_for_status()
        items = resp.json().get("message", {}).get("items", [])
        return [_parse_item(item) for item in items]
    except Exception as exc:  # noqa: BLE001
        logger.warning("CrossRef title search failed for %r: %s", title, exc)
        return []


def resolve_citation(query: str) -> CitationMetadata | None:
    """
    `query` may be a DOI (raw or as a doi.org URL) or a free-text title/
    reference string. Returns parsed metadata, or None if nothing matched.
    """
    query = query.strip()
    if query.lower().startswith("10.") or "doi.org" in query.lower():
        doi = query.split("doi.org/")[-1].strip("/")
        result = lookup_by_doi(doi)
        if result:
            return result
        return None

    results = search_by_title(query, rows=1)
    return results[0] if results else None
