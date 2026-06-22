"""Report browsing + feedback routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import FeedbackCreateRequest, FeedbackResponse, ReportSummary
from app.db import crud
from app.db.session import get_db

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("", response_model=list[ReportSummary])
async def list_reports(
    limit: int = 20, offset: int = 0, db: AsyncSession = Depends(get_db)
) -> list[ReportSummary]:
    reports = await crud.list_reports(db, limit=limit, offset=offset)
    return [ReportSummary.model_validate(r, from_attributes=True) for r in reports]


@router.get("/{report_id}", response_model=ReportSummary)
async def get_report(
    report_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> ReportSummary:
    report = await crud.get_report(db, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportSummary.model_validate(report, from_attributes=True)


@router.post("/{report_id}/feedback", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    report_id: uuid.UUID,
    payload: FeedbackCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    report = await crud.get_report(db, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    feedback = await crud.create_feedback(
        db, report_id, payload.rating, payload.comment
    )
    return FeedbackResponse.model_validate(feedback, from_attributes=True)
