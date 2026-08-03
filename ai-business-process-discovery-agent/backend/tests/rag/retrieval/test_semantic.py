import pytest

from app.rag.embeddings import EmbeddedChunk, EmbeddingProvider
from app.rag.retrieval import (
    RetrievalRequest,
    RetrievalValidationError,
    SemanticRetriever,
)
from app.rag.vector_store import InMemoryVectorStore


class QueryProvider(EmbeddingProvider):
    @property
    def provider_name(self) -> str:
        return "test-provider"

    @property
    def model_name(self) -> str:
        return "test-model"

    @property
    def embedding_dimension(self) -> int:
        return 2

    def embed_text(self, text: str) -> list[float]:
        return [1.0, 0.0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]


def make_chunk(
    chunk_id: str,
    vector: list[float],
    *,
    document_id: str = "doc-1",
    metadata: dict | None = None,
) -> EmbeddedChunk:
    return EmbeddedChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        text=f"Text {chunk_id}",
        embedding=vector,
        chunk_index=0,
        metadata=metadata or {},
        provider="test-provider",
        model="test-model",
    )


def make_retriever() -> SemanticRetriever:
    store = InMemoryVectorStore(2)
    store.add_chunks(
        [
            make_chunk("best", [1.0, 0.0], metadata={"kind": "policy"}),
            make_chunk("second", [0.8, 0.6], metadata={"kind": "guide"}),
            make_chunk(
                "other-document",
                [0.6, 0.8],
                document_id="doc-2",
                metadata={"kind": "policy"},
            ),
            make_chunk("opposite", [-1.0, 0.0]),
        ]
    )
    return SemanticRetriever(QueryProvider(), store)


def test_semantic_retrieval_returns_ranked_results() -> None:
    response = make_retriever().retrieve(RetrievalRequest(query="approval process"))
    assert [result.chunk_id for result in response.results] == [
        "best", "second", "other-document", "opposite"
    ]
    assert [result.score for result in response.results] == sorted(
        [result.score for result in response.results], reverse=True
    )


def test_top_k_limits_results() -> None:
    response = make_retriever().retrieve(RetrievalRequest(query="approval", top_k=2))
    assert response.result_count == 2
    assert [result.chunk_id for result in response.results] == ["best", "second"]


def test_document_and_metadata_filters() -> None:
    retriever = make_retriever()
    document = retriever.retrieve(RetrievalRequest(query="approval", document_id="doc-2"))
    metadata = retriever.retrieve(RetrievalRequest(query="approval", metadata_filters={"kind": "policy"}))
    assert [result.chunk_id for result in document.results] == ["other-document"]
    assert [result.chunk_id for result in metadata.results] == ["best", "other-document"]


def test_minimum_score_filters_results() -> None:
    response = make_retriever().retrieve(
        RetrievalRequest(query="approval", minimum_score=0.7)
    )
    assert [result.chunk_id for result in response.results] == ["best", "second"]


def test_empty_query_is_rejected() -> None:
    with pytest.raises(RetrievalValidationError, match="must not be empty"):
        make_retriever().retrieve(RetrievalRequest(query="  "))


def test_no_result_case() -> None:
    response = make_retriever().retrieve(
        RetrievalRequest(query="approval", document_id="missing")
    )
    assert response.result_count == 0
    assert response.results == []


def test_response_includes_query_and_provider_metadata() -> None:
    response = make_retriever().retrieve(RetrievalRequest(query="approval"))
    assert response.query == "approval"
    assert response.provider == "test-provider"
    assert response.model == "test-model"
