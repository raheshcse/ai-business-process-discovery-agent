import hashlib
import math

from app.rag.embeddings.base import EmbeddingProvider


class DeterministicLocalEmbeddingProvider(EmbeddingProvider):
    """Offline deterministic embeddings intended for development and tests."""

    def __init__(self, dimension: int = 128) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be greater than zero")
        self._dimension = dimension

    @property
    def provider_name(self) -> str:
        return "local-deterministic"

    @property
    def model_name(self) -> str:
        return "shake-256-v1"

    @property
    def embedding_dimension(self) -> int:
        return self._dimension

    def embed_text(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Text to embed must not be empty")

        digest = hashlib.shake_256(text.encode("utf-8")).digest(
            self._dimension * 2
        )
        vector = [
            (int.from_bytes(digest[index : index + 2], "big") / 32767.5) - 1.0
            for index in range(0, len(digest), 2)
        ]
        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            return vector
        return [value / magnitude for value in vector]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]
