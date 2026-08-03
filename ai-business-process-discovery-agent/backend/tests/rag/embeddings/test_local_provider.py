import math

import pytest

from app.rag.embeddings import DeterministicLocalEmbeddingProvider


def test_single_text_embedding() -> None:
    provider = DeterministicLocalEmbeddingProvider(dimension=16)

    vector = provider.embed_text("Approve the purchase request")

    assert len(vector) == 16
    assert all(isinstance(value, float) for value in vector)
    assert math.isclose(math.sqrt(sum(value * value for value in vector)), 1.0)


def test_batch_embedding_preserves_order() -> None:
    provider = DeterministicLocalEmbeddingProvider(dimension=8)
    texts = ["First process", "Second process"]

    vectors = provider.embed_batch(texts)

    assert len(vectors) == 2
    assert vectors[0] == provider.embed_text(texts[0])
    assert vectors[1] == provider.embed_text(texts[1])
    assert vectors[0] != vectors[1]


def test_embedding_output_is_deterministic() -> None:
    first_provider = DeterministicLocalEmbeddingProvider(dimension=32)
    second_provider = DeterministicLocalEmbeddingProvider(dimension=32)

    first = first_provider.embed_text("Stable document content")
    second = second_provider.embed_text("Stable document content")

    assert first == second


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_empty_text_is_rejected(text: str) -> None:
    provider = DeterministicLocalEmbeddingProvider()

    with pytest.raises(ValueError, match="must not be empty"):
        provider.embed_text(text)


def test_batch_rejects_an_empty_text() -> None:
    provider = DeterministicLocalEmbeddingProvider()

    with pytest.raises(ValueError, match="must not be empty"):
        provider.embed_batch(["valid", " "])


def test_empty_batch_returns_empty_list() -> None:
    provider = DeterministicLocalEmbeddingProvider()

    assert provider.embed_batch([]) == []


def test_invalid_dimension_is_rejected() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        DeterministicLocalEmbeddingProvider(dimension=0)
