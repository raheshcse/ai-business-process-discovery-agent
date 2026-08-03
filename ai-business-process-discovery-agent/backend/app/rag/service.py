from dataclasses import dataclass
from typing import Any

from app.rag.chunking import DocumentChunk
from app.rag.context import AssembledContext, ContextAssembler
from app.rag.embeddings import EmbeddingProvider, EmbeddingService
from app.rag.retrieval import Retriever, RetrievalRequest, RetrievalResponse
from app.rag.vector_store import VectorStore


@dataclass(frozen=True)
class IndexingResult:
    requested_count: int
    indexed_count: int
    total_count: int
    provider: str
    model: str


@dataclass(frozen=True)
class RAGResult:
    retrieval: RetrievalResponse
    context: AssembledContext


@dataclass(frozen=True)
class DeletionResult:
    document_id: str
    deleted_count: int
    total_count: int


class RAGService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        retriever: Retriever,
        context_assembler: ContextAssembler,
    ) -> None:
        self._embedding_service = embedding_service
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store
        self._retriever = retriever
        self._context_assembler = context_assembler

    def index_chunks(self, chunks: list[DocumentChunk]) -> IndexingResult:
        count_before = self._vector_store.count()
        self._vector_store.add_chunks(self._embedding_service.embed_chunks(chunks))
        total_count = self._vector_store.count()
        return IndexingResult(
            requested_count=len(chunks),
            indexed_count=total_count - count_before,
            total_count=total_count,
            provider=self._embedding_provider.provider_name,
            model=self._embedding_provider.model_name,
        )

    def retrieve(self, request: RetrievalRequest) -> RAGResult:
        retrieval = self._retriever.retrieve(request)
        return RAGResult(
            retrieval=retrieval,
            context=self._context_assembler.assemble(retrieval.results),
        )

    def query(
        self,
        query: str,
        *,
        top_k: int = 5,
        document_id: str | None = None,
        metadata_filters: dict[str, Any] | None = None,
        minimum_score: float | None = None,
    ) -> RAGResult:
        return self.retrieve(
            RetrievalRequest(
                query=query,
                top_k=top_k,
                document_id=document_id,
                metadata_filters=dict(metadata_filters or {}),
                minimum_score=minimum_score,
            )
        )

    def delete_by_document(self, document_id: str) -> DeletionResult:
        count_before = self._vector_store.count()
        self._vector_store.delete_by_document(document_id)
        total_count = self._vector_store.count()
        return DeletionResult(
            document_id=document_id,
            deleted_count=count_before - total_count,
            total_count=total_count,
        )
