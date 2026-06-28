"""
Pydantic models that flow through the agent graph and are eventually
serialized as the final report JSON. Kept separate from `state.py` (the
LangGraph TypedDict) because these are also reused by the FastAPI response
schemas and the DB layer.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SubtaskType(StrEnum):
    WEB_SEARCH = "web_search"
    PDF_READER = "pdf_reader"
    CODE_EXEC = "code_exec"
    FACT_CHECK = "fact_check"


class Subtask(BaseModel):
    id: str = Field(description="short stable id, e.g. 't1', 't2'")
    type: SubtaskType = Field(
        description="one of: web_search, pdf_reader, code_exec, fact_check"
    )
    description: str = Field(
        description="what this subtask should find out, written for the specialist agent"
    )
    input_data: str = Field(
        default="",
        description="extra payload the subtask needs: a URL for pdf_reader, a data/spec description for "
        "code_exec, or a specific claim to verify for fact_check. Empty string if not applicable.",
    )


class ResearchPlan(BaseModel):
    objective: str = Field(
        description="one-sentence restatement of what the research run is trying to answer"
    )
    subtasks: list[Subtask] = Field(
        description="the decomposed list of subtasks to dispatch to specialist agents"
    )


class SourceRef(BaseModel):
    url: str | None = None
    title: str | None = None
    doi: str | None = None

    def dedup_key(self) -> str:
        return (self.doi or self.url or self.title or "").strip().lower()


class SubtaskResult(BaseModel):
    subtask_id: str
    subtask_type: SubtaskType
    summary: str
    sources: list[SourceRef] = Field(default_factory=list)
    confidence: float = 0.5
    raw_excerpt: str = ""
    error: str | None = None


class FactCheckVerdict(BaseModel):
    claim: str
    verdict: str = Field(description="one of: supported, contradicted, uncertain")
    explanation: str
    sources: list[SourceRef] = Field(default_factory=list)


class FactCheckClaimList(BaseModel):
    """Intermediate structured-output shape: the LLM extracts the report's
    checkable factual claims as a flat list before each gets verified."""

    claims: list[str]


class Citation(BaseModel):
    id: str
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    url: str | None = None
    doi: str | None = None

    def formatted(self) -> str:
        author_str = ", ".join(self.authors[:3]) + (
            " et al." if len(self.authors) > 3 else ""
        )
        year_str = f" ({self.year})" if self.year else ""
        venue_str = f". {self.venue}" if self.venue else ""
        link = self.doi and f"https://doi.org/{self.doi}" or self.url or ""
        title = self.title or "Untitled source"
        pieces = [p for p in [author_str, year_str.strip(), title, venue_str] if p]
        base = " ".join(pieces).strip()
        return f"{base} {link}".strip()


class ReportSection(BaseModel):
    heading: str
    content: str
    citation_ids: list[str] = Field(default_factory=list)


class ResearchReport(BaseModel):
    title: str
    summary: str
    sections: list[ReportSection]
    citations: list[Citation]
    confidence_score: float = Field(ge=0.0, le=1.0)
