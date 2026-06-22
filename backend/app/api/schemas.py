"""Pydantic schemas for the FastAPI request/response bodies. Kept separate
from `app/agents/schemas.py` (the internal agent-graph models), these are
the public API contract and are allowed to evolve independently."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ResearchCreateRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)


class ResearchCreateResponse(BaseModel):
    session_id: uuid.UUID
    status: str


class ReviewDecisionRequest(BaseModel):
    approved: bool
    feedback: str | None = Field(default=None, max_length=2000)


class ReportSummary(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    title: str
    summary: str
    sections: list[dict]
    citations: list[dict]
    confidence_score: float
    created_at: datetime

    model_config = {"from_attributes": True}


class ResearchSessionResponse(BaseModel):
    id: uuid.UUID
    query: str
    status: str
    plan: dict | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    report: ReportSummary | None = None

    model_config = {"from_attributes": True}


class FeedbackCreateRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class FeedbackResponse(BaseModel):
    id: uuid.UUID
    report_id: uuid.UUID
    rating: int
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
