"""
Embeddings factory.

Default: BAAI/bge-small-en-v1.5 via `langchain_huggingface`, running fully
locally through `sentence-transformers`. No API key, no per-call cost,
no network dependency once the model weights are cached (~130MB, cached
under ~/.cache/huggingface after the first call).

Alternative: OpenAI's text-embedding-3-small, if the we set
EMBEDDING_PROVIDER=openai and supplies OPENAI_API_KEY, slightly higher
retrieval quality at a small per-token cost.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings

from app.config import settings


@lru_cache
def get_embeddings() -> Embeddings:
    if settings.embedding_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError(
                "EMBEDDING_PROVIDER=openai but OPENAI_API_KEY is not set. "
                "Either set OPENAI_API_KEY or switch EMBEDDING_PROVIDER=huggingface."
            )
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=settings.openai_embedding_model, api_key=settings.openai_api_key
        )

    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=settings.huggingface_embedding_model,
        encode_kwargs={"normalize_embeddings": True},
    )
