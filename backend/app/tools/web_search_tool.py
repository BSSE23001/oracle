"""
Web search tool: Tavily, which is purpose-built for LLM agent consumption
(it returns clean extracted content and relevance scores, not raw SERP HTML).
"""

from __future__ import annotations

import logging
from typing import TypedDict

from tavily import TavilyClient

from app.config import settings

logger = logging.getLogger("oracle.tools.web_search")


class WebSearchHit(TypedDict):
    title: str
    url: str
    content: str
    score: float


_client: TavilyClient | None = None


def _get_client() -> TavilyClient:
    global _client
    if _client is None:
        if not settings.tavily_api_key:
            raise RuntimeError(
                "TAVILY_API_KEY is not set. Copy backend/.env.example to "
                "backend/.env and fill it in. For this see docs/GET_API_KEYS.md."
            )
        _client = TavilyClient(api_key=settings.tavily_api_key)
    return _client


def web_search(
    query: str, max_results: int = 5, search_depth: str = "advanced"
) -> list[WebSearchHit]:
    """
    Run a Tavily search and return a clean list of hits.
    `search_depth="advanced"` costs more Tavily credits but returns better
    extracted page content which is worth it for research-quality summarization.
    """
    try:
        client = _get_client()
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth=search_depth,
            include_answer=False,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Tavily search failed for query %r: %s", query, exc)
        return []

    hits: list[WebSearchHit] = []
    for item in response.get("results", []):
        hits.append(
            WebSearchHit(
                title=item.get("title", ""),
                url=item.get("url", ""),
                content=item.get("content", ""),
                score=float(item.get("score", 0.0)),
            )
        )
    return hits


def format_hits_for_prompt(hits: list[WebSearchHit]) -> str:
    """Render search hits as a numbered source list an LLM can cite by index."""
    if not hits:
        return "(no search results found)"
    lines = []
    for i, hit in enumerate(hits, start=1):
        snippet = hit["content"][:1200].strip()
        lines.append(f"[{i}] {hit['title']}\nURL: {hit['url']}\n{snippet}\n")
    return "\n".join(lines)
