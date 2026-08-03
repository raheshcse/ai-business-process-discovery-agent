import pytest

from app.rag.chunking import DocumentChunk
from app.rag.context import ContextAssembler
from app.rag.embeddings import EmbeddingProvider, EmbeddingService
from app.rag.retrieval import RetrievalValidationError, SemanticRetriever
from app.rag.service import RAGService
from app.rag.vector_store import InMemoryVectorStore


class TestProvider(EmbeddingProvider):
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
        text = text.lower()
        if "approval" in text:
            return [1.0, 0.0]
        if "invoice" in text:
            return [0.8, 0.6]
        return [0.0, 1.0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]


def chunk(chunk_id: str, text: str, document_id: str = "doc-1") -> DocumentChunk:
    return DocumentChunk(
        id=chunk_id,
        document_id=document_id,
        text=text,
        chunk_index=0,
        start_character=0,
        end_character=len(text),
        word_count=len(text.split()),
        metadata={"kind": "process"},
    )


def service() -> RAGService:
    provider = TestProvider()
    store = InMemoryVectorStore(2)
    return RAGService(
        EmbeddingService(provider),
        provider,
        store,
        SemanticRetriever(provider, store),
        ContextAssembler(),
    )


def test_indexes_chunks_with_typed_counts() -> None:
    rag = service()
    result = rag.index_chunks([chunk("approval", "Approval workflow")])
    assert (result.requested_count, result.indexed_count, result.total_count) == (1, 1, 1)
    assert (result.provider, result.model) == ("test-provider", "test-model")


def test_queries_indexed_chunks_in_correct_ranking() -> None:
    rag = service()
    rag.index_chunks([
        chunk("other", "Employee onboarding"),
        chunk("invoice", "Invoice processing"),
        chunk("approval", "Approval workflow"),
    ])
    response = rag.query("approval")
    assert [item.chunk_id for item in response.retrieval.results] == [
        "approval", "invoice", "other"
    ]


def test_query_generates_ranked_context() -> None:
    rag = service()
    rag.index_chunks([
        chunk("approval", "Approval workflow"),
        chunk("invoice", "Invoice processing"),
    ])
    response = rag.query("approval", top_k=2)
    assert response.context.source_count == 2
    assert response.context.combined_context.startswith("[Source 1]\nApproval workflow")
    assert [citation.chunk_id for citation in response.context.citations] == [
        "approval", "invoice"
    ]


def test_deletes_document_chunks() -> None:
    rag = service()
    rag.index_chunks([
        chunk("approval", "Approval", "doc-1"),
        chunk("invoice", "Invoice", "doc-2"),
    ])
    deleted = rag.delete_by_document("doc-1")
    assert (deleted.deleted_count, deleted.total_count) == (1, 1)
    assert rag.query("approval").retrieval.results[0].chunk_id == "invoice"


def test_empty_query_is_rejected() -> None:
    with pytest.raises(RetrievalValidationError, match="must not be empty"):
        service().query("  ")


def test_no_indexed_data_returns_empty_results_and_context() -> None:
    response = service().query("approval")
    assert response.retrieval.result_count == 0
    assert response.context.source_count == 0
    assert response.context.combined_context == ""
