from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the stable name of the embedding provider."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the provider-specific embedding model name."""

    @property
    @abstractmethod
    def embedding_dimension(self) -> int:
        """Return the number of values in each embedding vector."""

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Embed one non-empty text value."""

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch while preserving input order."""
