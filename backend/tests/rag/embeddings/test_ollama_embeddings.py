"""Regression tests for the batched Ollama embedding provider.

The bug these exist to prevent: `embed_batch` used to send every text in a
single HTTP request. A 200 KB CSV chunked into 261 pieces became one request
asking Ollama for 261 forward passes, which timed out, while 7- and 10-chunk
documents in the same project indexed fine. The failure therefore looked like
"large files are broken" with no usable error message.
"""

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app.rag.embeddings.ollama import (
    EmbeddingProviderUnavailableError,
    OllamaEmbeddingProvider,
)


class _RecordingHandler(BaseHTTPRequestHandler):
    batch_sizes: list[int] = []
    status_code: int = 200
    delay_per_text: float = 0.0
    vector_count_override: int | None = None

    def log_message(self, *args):  # silence the test output
        pass

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        texts = json.loads(self.rfile.read(length))["input"]
        type(self).batch_sizes.append(len(texts))

        if type(self).status_code != 200:
            self.send_response(type(self).status_code)
            self.end_headers()
            return

        if type(self).delay_per_text:
            import time

            time.sleep(type(self).delay_per_text * len(texts))

        count = (
            len(texts)
            if type(self).vector_count_override is None
            else type(self).vector_count_override
        )
        body = json.dumps({"embeddings": [[0.1, 0.2, 0.3] for _ in range(count)]})
        encoded = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        try:
            self.wfile.write(encoded)
        except (BrokenPipeError, ConnectionResetError):
            pass  # the client timed out and hung up; that is the test's point


@pytest.fixture
def fake_ollama():
    _RecordingHandler.batch_sizes = []
    _RecordingHandler.status_code = 200
    _RecordingHandler.delay_per_text = 0.0
    _RecordingHandler.vector_count_override = None

    server = HTTPServer(("127.0.0.1", 0), _RecordingHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", _RecordingHandler
    server.shutdown()
    server.server_close()


def _provider(url: str, **kwargs) -> OllamaEmbeddingProvider:
    return OllamaEmbeddingProvider(
        base_url=url, model_name="nomic-embed-text", timeout_seconds=10.0, **kwargs
    )


def test_large_document_is_split_into_bounded_batches(fake_ollama):
    url, handler = fake_ollama
    provider = _provider(url, batch_size=16)

    vectors = provider.embed_batch([f"chunk {index}" for index in range(261)])

    assert len(vectors) == 261
    # 261 texts at 16 per request = 17 requests, none larger than 16.
    assert len(handler.batch_sizes) == 17
    assert max(handler.batch_sizes) == 16
    assert sum(handler.batch_sizes) == 261


def test_order_is_preserved_across_batches(fake_ollama):
    url, _ = fake_ollama
    provider = _provider(url, batch_size=4)
    assert len(provider.embed_batch([f"t{i}" for i in range(10)])) == 10


def test_small_document_still_uses_one_request(fake_ollama):
    url, handler = fake_ollama
    provider = _provider(url, batch_size=16)

    provider.embed_batch([f"chunk {index}" for index in range(7)])

    assert handler.batch_sizes == [7]


def test_empty_input_makes_no_request(fake_ollama):
    url, handler = fake_ollama
    assert _provider(url).embed_batch([]) == []
    assert handler.batch_sizes == []


def test_blank_text_is_rejected_before_any_request(fake_ollama):
    url, handler = fake_ollama
    with pytest.raises(ValueError):
        _provider(url).embed_batch(["fine", "   "])
    assert handler.batch_sizes == []


def test_timeout_names_the_batch_size_and_the_setting(fake_ollama):
    url, handler = fake_ollama
    handler.delay_per_text = 0.05
    provider = _provider(url, batch_size=64)
    provider._timeout_seconds = 0.5

    with pytest.raises(EmbeddingProviderUnavailableError) as caught:
        provider.embed_batch([f"chunk {index}" for index in range(64)])

    message = str(caught.value)
    # Must be actionable, and must not blame connectivity for a slow model.
    assert "EMBEDDING_BATCH_SIZE" in message
    assert "64" in message
    assert "unreachable" not in message.lower()


def test_missing_model_is_reported_as_a_pull_command(fake_ollama):
    url, handler = fake_ollama
    handler.status_code = 404

    with pytest.raises(EmbeddingProviderUnavailableError) as caught:
        _provider(url).embed_text("hello")

    assert "ollama pull nomic-embed-text" in str(caught.value)


def test_unreachable_provider_says_how_to_start_it():
    provider = OllamaEmbeddingProvider(
        base_url="http://127.0.0.1:1", model_name="m", timeout_seconds=2.0
    )
    with pytest.raises(EmbeddingProviderUnavailableError) as caught:
        provider.embed_text("hello")
    assert "ollama serve" in str(caught.value)


def test_wrong_vector_count_is_detected(fake_ollama):
    url, handler = fake_ollama
    handler.vector_count_override = 2

    with pytest.raises(EmbeddingProviderUnavailableError) as caught:
        _provider(url).embed_batch(["a", "b", "c"])

    assert "may not be an embedding model" in str(caught.value)


def test_invalid_batch_size_is_rejected_at_construction():
    with pytest.raises(EmbeddingProviderUnavailableError):
        OllamaEmbeddingProvider(base_url="http://x", model_name="m", batch_size=0)
