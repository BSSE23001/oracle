"""
Vector store tool: local persistent Chroma collection used to ingest PDF /
web content per research session and retrieve relevant chunks for the
synthesis agent (lightweight RAG over whatever this run has gathered).

Swapping in Qdrant instead: the embedding + chunking logic here is
store-agnostic. Replace `_get_collection()` and the three public functions
below with equivalents against `qdrant_client.QdrantClient` and the rest of
the codebase (agents call only `ingest_document` / `query_similar` /
`reset_session`) needs no changes. We default to Chroma because it needs
zero external service for local dev (just a directory on disk), where
Qdrant wants either a running server or its (heavier) embedded mode.
"""

from __future__ import annotations

import hashlib
import logging
from functools import lru_cache
from typing import TypedDict

import chromadb

from app.config import settings
from app.core.embeddings import get_embeddings

logger = logging.getLogger("oracle.tools.vector_store")


class RetrievedChunk(TypedDict):
    text: str
    source: str
    score: float


@lru_cache
def _get_client() -> chromadb.ClientAPI:
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)


@lru_cache
def _get_collection():
    client = _get_client()
    return client.get_or_create_collection(name=settings.chroma_collection_name)


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def ingest_document(
    session_id: str, source: str, text: str, extra_metadata: dict | None = None
) -> int:
    """Chunk + embed + store `text` under `session_id` so it can be retrieved
    later in this research run. Returns the number of chunks stored."""
    chunks = chunk_text(text)
    if not chunks:
        return 0

    embeddings_model = get_embeddings()
    vectors = embeddings_model.embed_documents(chunks)

    source_hash = hashlib.sha1(source.encode("utf-8")).hexdigest()[:10]
    ids = [f"{session_id}:{source_hash}:{i}" for i in range(len(chunks))]
    metadatas = [
        {"session_id": session_id, "source": source, **(extra_metadata or {})}
        for _ in chunks
    ]

    collection = _get_collection()
    try:
        collection.upsert(
            ids=ids, embeddings=vectors, documents=chunks, metadatas=metadatas
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Chroma upsert failed for source %r: %s", source, exc)
        return 0
    return len(chunks)


def query_similar(session_id: str, query: str, k: int = 5) -> list[RetrievedChunk]:
    """Retrieve the top-k chunks most similar to `query`, scoped to this session."""
    embeddings_model = get_embeddings()
    query_vector = embeddings_model.embed_query(query)

    collection = _get_collection()
    try:
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=k,
            where={"session_id": session_id},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Chroma query failed: %s", exc)
        return []

    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    out: list[RetrievedChunk] = []
    for doc, meta, dist in zip(documents, metadatas, distances):
        # Chroma returns a distance (lower = more similar); convert to a
        # 0-1 "similarity-ish" score for display purposes.
        score = max(0.0, 1.0 - float(dist))
        out.append(
            RetrievedChunk(
                text=doc, source=(meta or {}).get("source", "unknown"), score=score
            )
        )
    return out


def reset_session(session_id: str) -> None:
    """Delete all chunks belonging to a session (e.g. on report finalisation
    or explicit user request) to keep the local Chroma store from growing
    unbounded across many research runs."""
    collection = _get_collection()
    try:
        collection.delete(where={"session_id": session_id})
    except Exception as exc:  # noqa: BLE001
        logger.warning("Chroma delete failed for session %r: %s", session_id, exc)
