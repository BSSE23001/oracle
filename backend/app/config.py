"""
Central configuration for ORACLE.

Everything the app needs to know about its environment lives here, loaded
once from `.env`.
Every other module imports `settings` from here rather than calling
`os.environ` directly and this keeps secrets out of business logic and makes
the whole app testable by overriding `Settings(...)` in tests.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────
    app_env: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"

    # ── OpenRouter (LLM) ─────────────────────────────────────────────────
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_models: str = (
        "meta-llama/llama-3.3-70b-instruct:free,"
        "qwen/qwen-2.5-72b-instruct:free,"
        "mistralai/mistral-7b-instruct:free"
    )
    openrouter_site_url: str = "http://localhost:3000"
    openrouter_site_name: str = "ORACLE Research Assistant"

    @property
    def openrouter_model_list(self) -> list[str]:
        return [m.strip() for m in self.openrouter_models.split(",") if m.strip()]

    # ── Tavily (web search) ─────────────────────────────────────────────
    tavily_api_key: str = ""

    # ── LangSmith (observability) ───────────────────────────────────────
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "oracle-research-assistant"
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    # ── CrossRef (citations) ────────────────────────────────────────────
    crossref_mailto: str = ""

    # ── Embeddings ───────────────────────────────────────────────────────
    embedding_provider: Literal["huggingface", "openai"] = "huggingface"
    huggingface_embedding_model: str = "BAAI/bge-small-en-v1.5"
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"

    # ── Chroma ───────────────────────────────────────────────────────────
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection_name: str = "oracle_documents"

    # ── Checkpointing ───────────────────────────────────────────────────
    checkpointer_backend: Literal["sqlite", "postgres"] = "sqlite"
    checkpointer_sqlite_path: str = "./data/checkpoints.sqlite"

    # ── Database ────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://oracle:oracle@localhost:5432/oracle"

    @property
    def database_url_sync(self) -> str:
        """SQLAlchemy sync (psycopg) variant of DATABASE_URL used by
        Celery tasks and Alembic, both of which go through SQLAlchemy's
        engine and so want the dialect+driver-qualified URL form."""
        return self.database_url.replace(
            "postgresql+asyncpg://", "postgresql+psycopg://"
        )

    @property
    def database_url_psycopg_raw(self) -> str:
        """Plain libpq-style connection string (no SQLAlchemy dialect
        prefix) required by langgraph's PostgresSaver, which calls
        `psycopg.connect()` directly rather than going through SQLAlchemy."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://")

    # ── API ─────────────────────────────────────────────────────────────
    cors_allow_origins: str = "http://localhost:3000"

    @property
    def cors_allow_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    # ── Queue ───────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ── Agent behaviour tuning ──────────────────────────────────────────
    max_subtasks_per_plan: int = 6
    agent_llm_timeout_seconds: int = 60
    code_exec_timeout_seconds: int = 15
    code_exec_max_output_chars: int = 8000

    @field_validator("crossref_mailto")
    @classmethod
    def _warn_empty_mailto(cls, v: str) -> str:
        # CrossRef works without this, just slower / lower priority queue.
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def configure_langsmith_env() -> None:
    """
    LangChain/LangSmith read tracing config from environment variables at
    import/call time, not from our Settings object. Call this once at
    process startup so every LangChain/LangGraph call downstream is automatically traced.
    """
    if settings.langsmith_tracing and settings.langsmith_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
        os.environ["LANGCHAIN_ENDPOINT"] = settings.langsmith_endpoint
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
