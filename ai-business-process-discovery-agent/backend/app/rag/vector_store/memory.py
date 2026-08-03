import math
from typing import Any

from app.rag.embeddings import EmbeddedChunk
from app.rag.vector_store.base import VectorStore
from app.rag.vector_store.models import SearchResult


class VectorStoreValidationError(ValueError):
    pass


class InMemoryVectorStore(VectorStore):
    def __init__(self, embedding_dimension: int | None = None) -> None:
        if embedding_dimension is not None and embedding_dimension <= 0:
            raise VectorStoreValidationError(
                "Embedding dimension must be greater than zero"
            )
        self._embedding_dimension = embedding_dimension
        self._chunks: dict[str, EmbeddedChunk] = {}

    def add_chunks(self, chunks: list[EmbeddedChunk]) -> None:
        new_chunks: list[EmbeddedChunk] = []
        seen = set(self._chunks)
        expected = self._embedding_dimension

        for chunk in chunks:
            if chunk.chunk_id in seen:
                continue
            if expected is None:
                expected = len(chunk.embedding)
                if expected <= 0:
                    raise VectorStoreValidationError(
                        "Embedding dimension must be greater than zero"
                    )
            self._validate_vector(chunk.embedding, expected, chunk.chunk_id)
            seen.add(chunk.chunk_id)
            new_chunks.append(chunk)

        if self._embedding_dimension is None and new_chunks:
            self._embedding_dimension = expected
        for chunk in new_chunks:
            self._chunks[chunk.chunk_id] = self._copy_chunk(chunk)

    def search(
        self,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        if top_k < 0:
            raise VectorStoreValidationError("top_k cannot be negative")
        if top_k == 0 or not self._chunks:
            return []

        dimension = self._embedding_dimension
        assert dimension is not None
        self._validate_vector(query_embedding, dimension, "query")
        query_norm = math.sqrt(sum(value * value for value in query_embedding))

        ranked: list[tuple[float, int, EmbeddedChunk]] = []
        for insertion_index, chunk in enumerate(self._chunks.values()):
            if not self._matches_filters(chunk, filters):
                continue
            chunk_norm = math.sqrt(sum(value * value for value in chunk.embedding))
            score = 0.0
            if query_norm and chunk_norm:
                score = sum(
                    query_value * chunk_value
                    for query_value, chunk_value in zip(
                        query_embedding, chunk.embedding
                    )
                ) / (query_norm * chunk_norm)
            ranked.append((score, insertion_index, chunk))

        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [
            SearchResult(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                text=chunk.text,
                score=score,
                chunk_index=chunk.chunk_index,
                metadata=dict(chunk.metadata),
            )
            for score, _, chunk in ranked[:top_k]
        ]

    def delete_by_document(self, document_id: str) -> None:
        self._chunks = {
            chunk_id: chunk
            for chunk_id, chunk in self._chunks.items()
            if chunk.document_id != document_id
        }

    def count(self) -> int:
        return len(self._chunks)

    @staticmethod
    def _validate_vector(vector: list[float], expected: int, label: str) -> None:
        if len(vector) != expected:
            raise VectorStoreValidationError(
                f"Embedding for {label!r} has dimension {len(vector)}; "
                f"expected {expected}"
            )
        try:
            finite = all(math.isfinite(value) for value in vector)
        except TypeError as exc:
            raise VectorStoreValidationError(
                f"Embedding for {label!r} contains a non-numeric value"
            ) from exc
        if not finite:
            raise VectorStoreValidationError(
                f"Embedding for {label!r} contains a non-finite value"
            )

    @staticmethod
    def _matches_filters(
        chunk: EmbeddedChunk, filters: dict[str, Any] | None
    ) -> bool:
        if not filters:
            return True
        if "document_id" in filters and chunk.document_id != filters["document_id"]:
            return False

        metadata_filters = filters.get("metadata", {})
        if not isinstance(metadata_filters, dict):
            return False
        metadata_filters = {
            **{key: value for key, value in filters.items() if key != "document_id" and key != "metadata"},
            **metadata_filters,
        }
        return all(chunk.metadata.get(key) == value for key, value in metadata_filters.items())

    @staticmethod
    def _copy_chunk(chunk: EmbeddedChunk) -> EmbeddedChunk:
        return EmbeddedChunk(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            text=chunk.text,
            embedding=list(chunk.embedding),
            chunk_index=chunk.chunk_index,
            metadata=dict(chunk.metadata),
            provider=chunk.provider,
            model=chunk.model,
        )
