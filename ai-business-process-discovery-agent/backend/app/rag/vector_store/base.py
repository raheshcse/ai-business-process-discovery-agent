from abc import ABC, abstractmethod
from typing import Any

from app.rag.embeddings import EmbeddedChunk
from app.rag.vector_store.models import SearchResult


class VectorStore(ABC):
    @abstractmethod
    def add_chunks(self, chunks: list[EmbeddedChunk]) -> None:
        """Add embedded chunks while ignoring chunk IDs already in the store."""

    @abstractmethod
    def search(
        self,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Return the most similar chunks that match the optional filters."""

    @abstractmethod
    def delete_by_document(self, document_id: str) -> None:
        """Delete every chunk belonging to a document."""

    @abstractmethod
    def count(self) -> int:
        """Return the number of stored chunks."""
