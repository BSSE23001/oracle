from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError

from app.tools import vector_store


class FakeClient:
    def __init__(self) -> None:
        self.collection = object()

    def get_or_create_collection(self, name: str):
        assert name
        return self.collection


def test_get_collection_does_not_deadlock_when_client_needs_lock(monkeypatch):
    fake_client = FakeClient()

    monkeypatch.setattr(vector_store, "_chroma_client", None)
    monkeypatch.setattr(vector_store, "_chroma_collection", None)
    monkeypatch.setattr(
        vector_store.chromadb,
        "PersistentClient",
        lambda path: fake_client,
    )

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(vector_store._get_collection)
        try:
            collection = future.result(timeout=1)
        except TimeoutError:
            future.cancel()
            raise AssertionError("_get_collection deadlocked while initialising Chroma")

    assert collection is fake_client.collection
