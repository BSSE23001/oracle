"""Shared pytest fixtures. Sets dummy env vars before any app module is
imported, so `Settings()` (which reads `.env`/the environment at import
time via `get_settings()`) never fails in CI for lack of real API keys."""
import os

os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("TAVILY_API_KEY", "test-key")
os.environ.setdefault("CHECKPOINTER_BACKEND", "sqlite")
os.environ.setdefault("CHECKPOINTER_SQLITE_PATH", "./data/test_checkpoints.sqlite")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
