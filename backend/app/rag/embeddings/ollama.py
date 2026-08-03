"""Embedding provider backed by Ollama's local embeddings endpoint.

The project already talks to Ollama for analysis. Reusing it for
embeddings turns retrieval from hash-deterministic into genuinely
semantic, which is what makes the evidence-score governance gate
meaningful. It is opt-in via `EMBEDDING_PROVIDER=ollama` so the default
setup still needs no model download.
"""

import json
import socket
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import settings
from app.rag.embeddings.base import EmbeddingProvider


class EmbeddingProviderUnavailableError(RuntimeError):
    pass


class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        resolved_base_url = base_url or settings.ollama_base_url
        resolved_model = model_name or settings.ollama_embedding_model
        resolved_timeout = (
            settings.ollama_timeout_seconds
            if timeout_seconds is None
            else timeout_seconds
        )
        if not resolved_base_url.strip():
            raise EmbeddingProviderUnavailableError(
                "OLLAMA_BASE_URL must not be empty"
            )
        if not resolved_model.strip():
            raise EmbeddingProviderUnavailableError(
                "OLLAMA_EMBEDDING_MODEL must not be empty"
            )

        self._base_url = resolved_base_url.rstrip("/")
        self._model_name = resolved_model
        self._timeout_seconds = resolved_timeout
        self._dimension: int | None = None

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def embedding_dimension(self) -> int:
        if self._dimension is None:
            # Probe once; the dimension is a property of the model and the
            # EmbeddingService needs it before the first real batch.
            self._dimension = len(self.embed_text("dimension probe"))
        return self._dimension

    def embed_text(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Text to embed must not be empty")
        return self._request([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        for text in texts:
            if not text.strip():
                raise ValueError("Text to embed must not be empty")
        return self._request(texts)

    def _request(self, texts: list[str]) -> list[list[float]]:
        body = json.dumps({"model": self._model_name, "input": texts}).encode("utf-8")
        request = Request(
            f"{self._base_url}/api/embed",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise EmbeddingProviderUnavailableError(
                f"Ollama embeddings returned HTTP {exc.code}"
            ) from exc
        except (URLError, socket.timeout, TimeoutError) as exc:
            raise EmbeddingProviderUnavailableError(
                "Ollama embeddings endpoint is unreachable"
            ) from exc
        except json.JSONDecodeError as exc:
            raise EmbeddingProviderUnavailableError(
                "Ollama embeddings returned a malformed response"
            ) from exc

        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise EmbeddingProviderUnavailableError(
                "Ollama embeddings returned an unexpected number of vectors"
            )
        return [[float(value) for value in vector] for vector in embeddings]
