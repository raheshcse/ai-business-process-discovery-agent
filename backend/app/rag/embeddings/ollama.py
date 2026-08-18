"""Embedding provider backed by Ollama's local embeddings endpoint.

The project already talks to Ollama for analysis. Reusing it for
embeddings turns retrieval from hash-deterministic into genuinely
semantic, which is what makes the evidence-score governance gate
meaningful. It is opt-in via `EMBEDDING_PROVIDER=ollama` so the default
setup still needs no model download.

Requests are batched. An earlier version sent every chunk of a document in
one call, which meant a 200 KB CSV became a single request asking Ollama to
run 261 forward passes before replying -- comfortably past any sane timeout
on CPU. Small documents indexed and large ones failed, which is a confusing
way for a system to break. Batching bounds the work per request so indexing
scales with document size instead of falling off a cliff.
"""

import json
import socket
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import settings
from app.rag.embeddings.base import EmbeddingProvider


class EmbeddingProviderUnavailableError(RuntimeError):
    """The embedding provider could not be reached or could not answer.

    Deliberately actionable: the message is shown directly to the user on
    the document row, so it names the fix rather than the stack frame.
    """


class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        timeout_seconds: float | None = None,
        batch_size: int | None = None,
    ) -> None:
        resolved_base_url = base_url or settings.ollama_base_url
        resolved_model = model_name or settings.ollama_embedding_model
        resolved_timeout = (
            settings.ollama_embedding_timeout_seconds
            if timeout_seconds is None
            else timeout_seconds
        )
        resolved_batch_size = (
            settings.embedding_batch_size if batch_size is None else batch_size
        )
        if not resolved_base_url.strip():
            raise EmbeddingProviderUnavailableError(
                "OLLAMA_BASE_URL must not be empty"
            )
        if not resolved_model.strip():
            raise EmbeddingProviderUnavailableError(
                "OLLAMA_EMBEDDING_MODEL must not be empty"
            )
        if resolved_timeout <= 0:
            raise EmbeddingProviderUnavailableError(
                "OLLAMA_EMBEDDING_TIMEOUT_SECONDS must be greater than zero"
            )
        if resolved_batch_size <= 0:
            raise EmbeddingProviderUnavailableError(
                "EMBEDDING_BATCH_SIZE must be greater than zero"
            )

        self._base_url = resolved_base_url.rstrip("/")
        self._model_name = resolved_model
        self._timeout_seconds = resolved_timeout
        self._batch_size = resolved_batch_size
        self._dimension: int | None = None

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def batch_size(self) -> int:
        return self._batch_size

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

        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            vectors.extend(self._request(texts[start : start + self._batch_size]))
        return vectors

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
            # 404 has two very different causes and the user needs to know
            # which: an Ollama too old for /api/embed, or a missing model.
            if exc.code == 404:
                raise EmbeddingProviderUnavailableError(
                    f"Ollama returned HTTP 404 for /api/embed. Either the model "
                    f"'{self._model_name}' is not installed (run: ollama pull "
                    f"{self._model_name}), or your Ollama version predates the "
                    f"/api/embed endpoint (run: ollama --version)."
                ) from exc
            raise EmbeddingProviderUnavailableError(
                f"Ollama embeddings returned HTTP {exc.code}."
            ) from exc
        except (socket.timeout, TimeoutError) as exc:
            raise EmbeddingProviderUnavailableError(
                f"Ollama did not return embeddings for {len(texts)} text(s) within "
                f"{self._timeout_seconds:.0f}s. The model is probably running on "
                f"CPU. Lower EMBEDDING_BATCH_SIZE (currently {self._batch_size}) "
                f"or raise OLLAMA_EMBEDDING_TIMEOUT_SECONDS."
            ) from exc
        except URLError as exc:
            # URLError wraps a socket timeout too, so check before blaming
            # connectivity -- reporting "unreachable" for a slow model is what
            # made this failure so hard to diagnose in the first place.
            if isinstance(exc.reason, (socket.timeout, TimeoutError)):
                raise EmbeddingProviderUnavailableError(
                    f"Ollama did not return embeddings for {len(texts)} text(s) "
                    f"within {self._timeout_seconds:.0f}s. Lower "
                    f"EMBEDDING_BATCH_SIZE (currently {self._batch_size}) or raise "
                    f"OLLAMA_EMBEDDING_TIMEOUT_SECONDS."
                ) from exc
            raise EmbeddingProviderUnavailableError(
                f"Cannot reach Ollama at {self._base_url}. Is it running? "
                f"Start it with: ollama serve"
            ) from exc
        except json.JSONDecodeError as exc:
            raise EmbeddingProviderUnavailableError(
                "Ollama embeddings returned a malformed response."
            ) from exc

        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise EmbeddingProviderUnavailableError(
                f"Ollama returned {len(embeddings) if isinstance(embeddings, list) else 0} "
                f"vectors for {len(texts)} text(s). The model "
                f"'{self._model_name}' may not be an embedding model."
            )
        return [[float(value) for value in vector] for vector in embeddings]
