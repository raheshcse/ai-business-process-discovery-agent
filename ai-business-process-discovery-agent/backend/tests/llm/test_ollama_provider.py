import json
import socket
from io import BytesIO
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from app.core.config import Settings
from app.llm import (
    BusinessAnalysisResult,
    InvalidStructuredOutputError,
    OllamaLLMProvider,
    ProviderRequestError,
    ProviderUnavailableError,
)


def test_ollama_is_the_configured_local_default() -> None:
    configured = Settings(_env_file=None)
    assert configured.llm_provider == "ollama"
    assert configured.ollama_base_url
    assert configured.ollama_model
    assert configured.ollama_timeout_seconds > 0


def analysis_payload() -> dict[str, Any]:
    return {
        "summary": "Approval is followed by manual entry.",
        "findings": [{
            "title": "Manual entry",
            "description": "Finance manually enters approved invoices.",
            "category": "bottleneck",
            "severity": "medium",
            "evidence_source_ids": ["Source 2"],
            "recommendation": "Assess automation feasibility.",
        }],
        "assumptions": [],
        "insufficient_evidence": ["No cycle-time data was supplied."],
        "confidence": 0.8,
    }


class FakeHTTPResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def ollama_response(content: str) -> bytes:
    return json.dumps({
        "model": "configured-model",
        "message": {"role": "assistant", "content": content},
        "done": True,
    }).encode("utf-8")


def test_structured_generation_posts_schema_and_validates_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(request: Request, timeout: float) -> FakeHTTPResponse:
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data or b"{}")
        return FakeHTTPResponse(
            ollama_response(json.dumps(analysis_payload()))
        )

    monkeypatch.setattr("app.llm.ollama_provider.urlopen", fake_urlopen)
    provider = OllamaLLMProvider(
        base_url="http://ollama.test:11434/",
        model_name="configured-model",
        timeout_seconds=12.5,
    )
    result = provider.generate(
        "system",
        "user",
        response_model=BusinessAnalysisResult,
        temperature=0.2,
        max_output_tokens=500,
    )

    assert isinstance(result, BusinessAnalysisResult)
    assert result.findings[0].evidence_source_ids == ["Source 2"]
    assert captured["url"] == "http://ollama.test:11434/api/chat"
    assert captured["timeout"] == 12.5
    assert captured["payload"]["model"] == "configured-model"
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["options"] == {
        "temperature": 0.2,
        "num_predict": 500,
    }
    assert captured["payload"]["format"]["title"] == "BusinessAnalysisResult"
    assert captured["payload"]["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "user"},
    ]
    assert provider.provider_name == "ollama"
    assert provider.model_name == "configured-model"


def test_plain_text_generation_returns_assistant_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.llm.ollama_provider.urlopen",
        lambda request, timeout: FakeHTTPResponse(ollama_response("fixed text")),
    )
    result = OllamaLLMProvider(
        base_url="http://ollama.test",
        model_name="configured-model",
    ).generate("system", "user")
    assert result == "fixed text"


def test_connection_error_maps_to_provider_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse_connection(request: Request, timeout: float) -> None:
        raise URLError(ConnectionRefusedError("refused"))

    monkeypatch.setattr(
        "app.llm.ollama_provider.urlopen", refuse_connection
    )
    with pytest.raises(ProviderUnavailableError, match="connect"):
        OllamaLLMProvider(
            base_url="http://ollama.test",
            model_name="configured-model",
        ).generate("system", "user")


@pytest.mark.parametrize(
    "error",
    [socket.timeout("timed out"), URLError(socket.timeout("timed out"))],
)
def test_timeout_maps_to_provider_request_error(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    def time_out(request: Request, timeout: float) -> None:
        raise error

    monkeypatch.setattr("app.llm.ollama_provider.urlopen", time_out)
    with pytest.raises(ProviderRequestError, match="timed out"):
        OllamaLLMProvider(
            base_url="http://ollama.test",
            model_name="configured-model",
        ).generate("system", "user")


def test_invalid_outer_json_maps_to_invalid_structured_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.llm.ollama_provider.urlopen",
        lambda request, timeout: FakeHTTPResponse(b"not json"),
    )
    with pytest.raises(InvalidStructuredOutputError, match="invalid JSON"):
        OllamaLLMProvider(
            base_url="http://ollama.test",
            model_name="configured-model",
        ).generate("system", "user")


def test_invalid_structured_content_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.llm.ollama_provider.urlopen",
        lambda request, timeout: FakeHTTPResponse(
            ollama_response('{"summary": "incomplete"}')
        ),
    )
    with pytest.raises(InvalidStructuredOutputError, match="response model"):
        OllamaLLMProvider(
            base_url="http://ollama.test",
            model_name="configured-model",
        ).generate(
            "system",
            "user",
            response_model=BusinessAnalysisResult,
        )


def test_model_error_payload_maps_to_provider_request_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = json.dumps({"error": "model not found"}).encode("utf-8")
    monkeypatch.setattr(
        "app.llm.ollama_provider.urlopen",
        lambda request, timeout: FakeHTTPResponse(body),
    )
    with pytest.raises(ProviderRequestError, match="model not found"):
        OllamaLLMProvider(
            base_url="http://ollama.test",
            model_name="missing-model",
        ).generate("system", "user")


def test_http_model_error_maps_to_provider_request_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def model_error(request: Request, timeout: float) -> None:
        raise HTTPError(
            request.full_url,
            404,
            "Not Found",
            {},
            BytesIO(b'{"error": "model unavailable"}'),
        )

    monkeypatch.setattr("app.llm.ollama_provider.urlopen", model_error)
    with pytest.raises(
        ProviderRequestError, match="HTTP 404: model unavailable"
    ):
        OllamaLLMProvider(
            base_url="http://ollama.test",
            model_name="missing-model",
        ).generate("system", "user")


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"base_url": " "}, "OLLAMA_BASE_URL"),
        ({"model_name": " "}, "OLLAMA_MODEL"),
        ({"timeout_seconds": 0}, "OLLAMA_TIMEOUT_SECONDS"),
    ],
)
def test_invalid_configuration_is_rejected(
    kwargs: dict[str, Any],
    message: str,
) -> None:
    defaults: dict[str, Any] = {
        "base_url": "http://ollama.test",
        "model_name": "configured-model",
        "timeout_seconds": 1,
    }
    defaults.update(kwargs)
    with pytest.raises(ProviderUnavailableError, match=message):
        OllamaLLMProvider(**defaults)
