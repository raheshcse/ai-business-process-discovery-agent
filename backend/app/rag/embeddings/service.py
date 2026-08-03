import math

from app.rag.chunking import DocumentChunk
from app.rag.embeddings.base import EmbeddingProvider
from app.rag.embeddings.models import EmbeddedChunk


class EmbeddingValidationError(ValueError):
    pass


class EmbeddingService:
    def __init__(self, provider: EmbeddingProvider) -> None:
        if provider.embedding_dimension <= 0:
            raise EmbeddingValidationError(
                "Provider embedding dimension must be greater than zero"
            )
        self._provider = provider

    def embed_chunk(self, chunk: DocumentChunk) -> EmbeddedChunk:
        embedded = self.embed_chunks([chunk])
        return embedded[0]

    def embed_chunks(self, chunks: list[DocumentChunk]) -> list[EmbeddedChunk]:
        if not chunks:
            return []
        for chunk in chunks:
            if not chunk.text.strip():
                raise EmbeddingValidationError(
                    f"Chunk {chunk.id!r} contains empty text"
                )

        vectors = self._provider.embed_batch([chunk.text for chunk in chunks])
        if len(vectors) != len(chunks):
            raise EmbeddingValidationError(
                "Provider returned a different number of vectors than input texts"
            )

        results: list[EmbeddedChunk] = []
        for chunk, vector in zip(chunks, vectors):
            self._validate_vector(vector, chunk.id)
            results.append(
                EmbeddedChunk(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    text=chunk.text,
                    embedding=list(vector),
                    chunk_index=chunk.chunk_index,
                    metadata=dict(chunk.metadata),
                    provider=self._provider.provider_name,
                    model=self._provider.model_name,
                )
            )
        return results

    def _validate_vector(self, vector: list[float], chunk_id: str) -> None:
        expected = self._provider.embedding_dimension
        if len(vector) != expected:
            raise EmbeddingValidationError(
                f"Embedding for chunk {chunk_id!r} has dimension {len(vector)}; "
                f"expected {expected}"
            )
        try:
            is_finite = all(math.isfinite(value) for value in vector)
        except TypeError as exc:
            raise EmbeddingValidationError(
                f"Embedding for chunk {chunk_id!r} contains a non-numeric value"
            ) from exc
        if not is_finite:
            raise EmbeddingValidationError(
                f"Embedding for chunk {chunk_id!r} contains a non-finite value"
            )
