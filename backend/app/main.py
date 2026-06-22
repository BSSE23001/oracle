"""
FastAPI application entrypoint.

Run with:
    uvicorn app.main:app --reload --port 8000

This process only ever talks to Postgres (session/report/event metadata)
and Redis (publishing nothing, only the Celery broker connection implied
by `.delay()` calls, and subscribing for SSE), it never builds or runs
the LangGraph graph itself. That happens entirely in the Celery worker
(`app/tasks/research_tasks.py`), which is what makes a research run
survive this process restarting.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_reports import router as reports_router
from app.api.routes_research import router as research_router
from app.config import configure_langsmith_env, settings
from app.core.logging_config import configure_logging

logger = logging.getLogger("oracle.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    configure_langsmith_env()
    logger.info("ORACLE API starting up (env=%s)", settings.app_env)
    yield
    logger.info("ORACLE API shutting down")


app = FastAPI(
    title="ORACLE Research Assistant API",
    description="Multi-agent research system — supervisor, specialist agents, synthesis, fact-checking, citations.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router)
app.include_router(reports_router)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok", "env": settings.app_env}
