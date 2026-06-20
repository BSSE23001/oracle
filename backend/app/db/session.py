"""
Two parallel SQLAlchemy setups against the same database:

  - Async engine/session (`asyncpg` driver), used by FastAPI request
    handlers, which are themselves async.
  - Sync engine/session (`psycopg` driver), used by Celery tasks, which
    run in plain synchronous worker processes. There's no benefit to
    forcing async machinery (asyncio.run(), etc.) inside a Celery task
    that's already running in its own dedicated process/thread.

Both point at the same Postgres database via `settings.database_url` /
`settings.database_url_sync`, only the driver differs.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings

# ── Async (FastAPI) ──────────────────────────────────────────────────────
# `poolclass=NullPool` + `statement_cache_size=0` look like overkill for a
# plain local Postgres connection, but they're required once DATABASE_URL
# points at Supabase's Supavisor pooler in transaction mode (port 6543,
# the recommended mode for serverless/many-short-lived-connections traffic
# like a web API): transaction mode reassigns the underlying server
# connection between statements, which breaks asyncpg's prepared-statement
# cache unless it's disabled, and SQLAlchemy should let Supavisor do the
# pooling rather than maintaining its own pool on top of it. Against local
# Postgres (docker-compose) these settings are harmless no-ops.
async_engine = create_async_engine(
    settings.database_url,
    poolclass=NullPool,
    pool_pre_ping=True,
    echo=False,
    connect_args=(
        {"statement_cache_size": 0, "prepared_statement_cache_size": 0}
        if "asyncpg" in settings.database_url
        else {}
    ),
)
AsyncSessionLocal = async_sessionmaker(
    async_engine, expire_on_commit=False, class_=AsyncSession
)


@asynccontextmanager
async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: `db: AsyncSession = Depends(get_db)`."""
    async with AsyncSessionLocal() as session:
        yield session


# ── Sync (Celery) ────────────────────────────────────────────────────────
sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True, echo=False)
SyncSessionLocal: sessionmaker[Session] = sessionmaker(
    sync_engine, expire_on_commit=False
)
