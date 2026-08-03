import pytest

from app.rag.embeddings import EmbeddedChunk
from app.rag.vector_store import InMemoryVectorStore, VectorStoreValidationError


def make_chunk(chunk_id: str, vector: list[float], document_id: str = "doc-1", metadata: dict | None = None) -> EmbeddedChunk:
    return EmbeddedChunk(chunk_id, document_id, chunk_id, vector, 0, metadata or {}, "test", "test")


def test_add_chunks_and_preserve_metadata() -> None:
    store = InMemoryVectorStore()
    item = make_chunk("a", [1.0, 0.0], metadata={"kind": "policy"})
    store.add_chunks([item])
    result = store.search([1.0, 0.0], 1)[0]
    assert store.count() == 1
    assert result.metadata == item.metadata and result.metadata is not item.metadata


def test_cosine_ranking_and_top_k() -> None:
    store = InMemoryVectorStore(2)
    store.add_chunks([make_chunk("best", [1.0, 0.0]), make_chunk("second", [1.0, 1.0]), make_chunk("last", [-1.0, 0.0])])
    assert [r.chunk_id for r in store.search([1.0, 0.0], 2)] == ["best", "second"]


def test_metadata_and_document_filters() -> None:
    store = InMemoryVectorStore(2)
    store.add_chunks([make_chunk("a", [1.0, 0.0], metadata={"kind": "policy"}), make_chunk("b", [1.0, 0.0], "doc-2", {"kind": "guide"})])
    assert [r.chunk_id for r in store.search([1.0, 0.0], 5, {"kind": "policy"})] == ["a"]
    assert [r.chunk_id for r in store.search([1.0, 0.0], 5, {"document_id": "doc-2"})] == ["b"]


def test_duplicate_chunk_ids_are_ignored_deterministically() -> None:
    store = InMemoryVectorStore(2)
    store.add_chunks([make_chunk("a", [1.0, 0.0]), make_chunk("a", [-1.0, 0.0]), make_chunk("b", [1.0, 0.0])])
    assert store.count() == 2
    assert [r.chunk_id for r in store.search([1.0, 0.0], 2)] == ["a", "b"]


def test_dimension_mismatch_is_atomic_and_query_is_validated() -> None:
    store = InMemoryVectorStore(2)
    with pytest.raises(VectorStoreValidationError, match="dimension 3; expected 2"):
        store.add_chunks([make_chunk("a", [1.0, 0.0]), make_chunk("bad", [1.0, 0.0, 0.0])])
    assert store.count() == 0
    store.add_chunks([make_chunk("a", [1.0, 0.0])])
    with pytest.raises(VectorStoreValidationError, match="dimension 1; expected 2"):
        store.search([1.0], 1)


def test_delete_by_document() -> None:
    store = InMemoryVectorStore(2)
    store.add_chunks([make_chunk("a", [1.0, 0.0]), make_chunk("b", [0.0, 1.0], "doc-2")])
    store.delete_by_document("doc-1")
    assert store.count() == 1
    assert store.search([0.0, 1.0], 1)[0].chunk_id == "b"


def test_empty_store_search() -> None:
    assert InMemoryVectorStore(2).search([1.0, 0.0], 5) == []
