import math
from typing import Any

from app.rag.embeddings import EmbeddingProvider
from app.rag.retrieval.base import Retriever
from app.rag.retrieval.models import RetrievalRequest, RetrievalResponse
from app.rag.vector_store import VectorStore


class RetrievalValidationError(ValueError):
    pass


class SemanticRetriever(Retriever):
    def __init__(self, embedding_provider: EmbeddingProvider, vector_store: VectorStore) -> None:
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store

    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        query = request.query.strip()
        if not query:
            raise RetrievalValidationError("Query must not be empty")
        if request.top_k < 0:
            raise RetrievalValidationError("top_k cannot be negative")
        if request.minimum_score is not None and not math.isfinite(request.minimum_score):
            raise RetrievalValidationError("minimum_score must be finite")

        results = self._vector_store.search(
            self._embedding_provider.embed_text(query),
            request.top_k,
            self._build_filters(request) or None,
        )
        if request.minimum_score is not None:
            results = [result for result in results if result.score >= request.minimum_score]
        results = sorted(results, key=lambda result: result.score, reverse=True)
        return RetrievalResponse(
            query=request.query,
            result_count=len(results),
            provider=self._embedding_provider.provider_name,
            model=self._embedding_provider.model_name,
            results=results,
        )

    @staticmethod
    def _build_filters(request: RetrievalRequest) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        if request.document_id is not None:
            filters["document_id"] = request.document_id
        if request.metadata_filters:
            filters["metadata"] = dict(request.metadata_filters)
        return filters
