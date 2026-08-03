from app.rag.chunking import DocumentChunk
from app.rag.embeddings import (
    DeterministicLocalEmbeddingProvider,
    EmbeddingProvider,
    EmbeddingService,
    EmbeddingValidationError,
)


def make_chunk(
    *,
    chunk_id: str = "chunk-1",
    text: str = "Review the submitted request",
    chunk_index: int = 0,
) -> DocumentChunk:
    return DocumentChunk(
        id=chunk_id,
        document_id="document-1",
        text=text,
        chunk_index=chunk_index,
        start_character=0,
        end_character=len(text),
        word_count=len(text.split()),
        metadata={"project_id": "project-1", "document_type": "pdf"},
    )


class WrongDimensionProvider(EmbeddingProvider):
    @property
    def provider_name(self) -> str:
        return "broken-provider"

    @property
    def model_name(self) -> str:
        return "broken-model"

    @property
    def embedding_dimension(self) -> int:
        return 3

    def embed_text(self, text: str) -> list[float]:
        return [1.0, 2.0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]


def test_service_preserves_chunk_fields_and_metadata() -> None:
    chunk = make_chunk()
    service = EmbeddingService(DeterministicLocalEmbeddingProvider(dimension=12))

    result = service.embed_chunk(chunk)

    assert result.chunk_id == chunk.id
    assert result.document_id == chunk.document_id
    assert result.text == chunk.text
    assert result.chunk_index == chunk.chunk_index
    assert result.metadata == chunk.metadata
    assert result.metadata is not chunk.metadata
    assert len(result.embedding) == 12


def test_service_sets_provider_and_model_metadata() -> None:
    provider = DeterministicLocalEmbeddingProvider(dimension=8)

    result = EmbeddingService(provider).embed_chunk(make_chunk())

    assert result.provider == provider.provider_name
    assert result.model == provider.model_name


def test_service_embeds_a_batch_in_chunk_order() -> None:
    chunks = [
        make_chunk(chunk_id="chunk-1", text="First", chunk_index=0),
        make_chunk(chunk_id="chunk-2", text="Second", chunk_index=1),
    ]

    results = EmbeddingService(
        DeterministicLocalEmbeddingProvider(dimension=8)
    ).embed_chunks(chunks)

    assert [result.chunk_id for result in results] == ["chunk-1", "chunk-2"]
    assert [result.chunk_index for result in results] == [0, 1]


def test_service_rejects_empty_chunk_text() -> None:
    service = EmbeddingService(DeterministicLocalEmbeddingProvider())

    try:
        service.embed_chunk(make_chunk(text=" "))
    except EmbeddingValidationError as exc:
        assert "empty text" in str(exc)
    else:
        raise AssertionError("Expected empty chunk text to be rejected")


def test_service_validates_provider_vector_dimension() -> None:
    service = EmbeddingService(WrongDimensionProvider())

    try:
        service.embed_chunk(make_chunk())
    except EmbeddingValidationError as exc:
        assert "dimension 2" in str(exc)
        assert "expected 3" in str(exc)
    else:
        raise AssertionError("Expected an invalid vector dimension to be rejected")


def test_service_accepts_an_empty_chunk_batch() -> None:
    service = EmbeddingService(DeterministicLocalEmbeddingProvider())

    assert service.embed_chunks([]) == []
