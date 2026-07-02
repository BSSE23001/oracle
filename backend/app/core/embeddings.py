"""
Embeddings factory.

Default: BAAI/bge-small-en-v1.5 via `langchain_huggingface`, running fully
locally through `sentence-transformers`. No API key, no per-call cost,
no network dependency once the model weights are cached (~130MB, cached
under ~/.cache/huggingface after the first call).

Alternative: OpenAI's text-embedding-3-small, if the we set
EMBEDDING_PROVIDER=openai and supplies OPENAI_API_KEY, slightly higher
retrieval quality at a small per-token cost.

Thread-safety note: `@lru_cache` is NOT safe for concurrent first calls.
If multiple threads call `get_embeddings()` simultaneously before the cache
is populated, all of them enter the factory function at the same time,
causing multiple simultaneous HuggingFaceEmbeddings initialisations — which
each trigger model downloads / GPU loads and produce multiple progress bars
in the logs (visible in the worker output as three concurrent loading bars).
The fix mirrors the double-checked locking pattern used in vector_store.py:
a module-level lock + a None-check inside the lock ensures only one thread
ever calls the expensive constructor.
"""

from __future__ import annotations

import threading

from langchain_core.embeddings import Embeddings

from app.config import settings

_embeddings_lock = threading.Lock()
_embeddings_instance: Embeddings | None = None


def get_embeddings() -> Embeddings:
    """Return the process-level cached embeddings model.

    Thread-safe: uses double-checked locking so only the first call ever
    constructs the model; subsequent calls return immediately without
    acquiring the lock.
    """
    global _embeddings_instance
    if _embeddings_instance is not None:
        return _embeddings_instance

    with _embeddings_lock:
        # Inner check: another thread may have constructed the instance
        # while we waited for the lock.
        if _embeddings_instance is not None:
            return _embeddings_instance

        if settings.embedding_provider == "openai":
            if not settings.openai_api_key:
                raise RuntimeError(
                    "EMBEDDING_PROVIDER=openai but OPENAI_API_KEY is not set. "
                    "Either set OPENAI_API_KEY or switch EMBEDDING_PROVIDER=huggingface."
                )
            from langchain_openai import OpenAIEmbeddings

            _embeddings_instance = OpenAIEmbeddings(
                model=settings.openai_embedding_model, api_key=settings.openai_api_key
            )
        else:
            from langchain_huggingface import HuggingFaceEmbeddings

            _embeddings_instance = HuggingFaceEmbeddings(
                model_name=settings.huggingface_embedding_model,
                encode_kwargs={"normalize_embeddings": True},
            )

    return _embeddings_instance
