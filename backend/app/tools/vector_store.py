"""
Vector store tool: local persistent Chroma collection used to ingest PDF /
web content per research session and retrieve relevant chunks for the
synthesis agent (lightweight RAG over whatever this run has gathered).

Thread-safety note: LangGraph's parallel Send fan-out runs specialist agents
in a ThreadPoolExecutor, so `ingest_document` (called by each agent after a
successful search/read) is called from multiple threads simultaneously on the
first research run. `@lru_cache` is NOT thread-safe for this: all N threads
can simultaneously enter `_get_client()` before any of them has populated the
cache, causing N simultaneous calls to `chromadb.PersistentClient(path=...)`.
Chroma's internal `SharedSystemClient._identifier_to_system` dict suffers a
write-then-read race, producing a `KeyError` on the return statement. The fix
is a module-level instance + a `threading.Lock` with double-checked locking so
only one thread ever calls `PersistentClient` and the rest wait for it.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from typing import TypedDict

import chromadb

from app.config import settings
from app.core.embeddings import get_embeddings

logger = logging.getLogger("oracle.tools.vector_store")

# ── Thread-safe singletons ───────────────────────────────────────────────────
# Double-checked locking: the fast path (non-None check) avoids acquiring the
# lock on every call after initialisation; the inner check inside the lock
# prevents duplicate initialisation if two threads both pass the outer check.

_chroma_lock = threading.Lock()
_chroma_client: chromadb.ClientAPI | None = None
_chroma_collection: chromadb.Collection | None = None


def _get_client() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        with _chroma_lock:
            if _chroma_client is None:
                logger.debug(
                    "Initialising Chroma PersistentClient at %s",
                    settings.chroma_persist_dir,
                )
                _chroma_client = chromadb.PersistentClient(
                    path=settings.chroma_persist_dir
                )
    return _chroma_client


def _get_collection() -> chromadb.Collection:
    global _chroma_collection
    if _chroma_collection is None:
        with _chroma_lock:
            if _chroma_collection is None:
                _chroma_collection = _get_client().get_or_create_collection(
                    name=settings.chroma_collection_name
                )
    return _chroma_collection


class RetrievedChunk(TypedDict):
    text: str
    source: str
    score: float


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
    for doc, meta, dist in zip(documents, metadatas, distances, strict=False):
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
