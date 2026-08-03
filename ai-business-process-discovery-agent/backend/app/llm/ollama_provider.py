import json
import socket
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import ValidationError

from app.core.config import settings
from app.llm.base import LLMProvider, ResponseModelT
from app.llm.exceptions import (
    InvalidStructuredOutputError,
    ProviderRequestError,
    ProviderUnavailableError,
)


class OllamaLLMProvider(LLMProvider):
    """LLM provider backed by Ollama's local HTTP chat API."""

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        resolved_base_url = base_url or settings.ollama_base_url
        resolved_model_name = model_name or settings.ollama_model
        resolved_timeout = (
            settings.ollama_timeout_seconds
            if timeout_seconds is None
            else timeout_seconds
        )
        if not resolved_base_url.strip():
            raise ProviderUnavailableError("OLLAMA_BASE_URL must not be empty")
        if not resolved_model_name.strip():
            raise ProviderUnavailableError("OLLAMA_MODEL must not be empty")
        if resolved_timeout <= 0:
            raise ProviderUnavailableError(
                "OLLAMA_TIMEOUT_SECONDS must be greater than zero"
            )

        self._base_url = resolved_base_url.rstrip("/")
        self._model_name = resolved_model_name
        self._timeout_seconds = resolved_timeout

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        response_model: type[ResponseModelT] | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> ResponseModelT | str:
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }
        options: dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_output_tokens is not None:
            options["num_predict"] = max_output_tokens
        if options:
            payload["options"] = options
        if response_model is not None:
            payload["format"] = response_model.model_json_schema()

        request = Request(
            f"{self._base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        response_data = self._send(request)
        content = self._extract_content(response_data)

        if response_model is None:
            return content
        try:
            return response_model.model_validate_json(content)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise InvalidStructuredOutputError(
                "Ollama response did not match the requested response model"
            ) from exc

    def _send(self, request: Request) -> dict[str, Any]:
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                raw_body = response.read()
        except HTTPError as exc:
            detail = self._read_http_error(exc)
            raise ProviderRequestError(
                f"Ollama model request failed with HTTP {exc.code}{detail}"
            ) from exc
        except (TimeoutError, socket.timeout) as exc:
            raise ProviderRequestError("Ollama request timed out") from exc
        except URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise ProviderRequestError("Ollama request timed out") from exc
            raise ProviderUnavailableError(
                "Unable to connect to the Ollama server"
            ) from exc
        except OSError as exc:
            raise ProviderUnavailableError(
                "Unable to connect to the Ollama server"
            ) from exc

        try:
            decoded = json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise InvalidStructuredOutputError(
                "Ollama returned an invalid JSON response"
            ) from exc
        if not isinstance(decoded, dict):
            raise InvalidStructuredOutputError(
                "Ollama returned an unexpected JSON response"
            )
        error = decoded.get("error")
        if error:
            raise ProviderRequestError(f"Ollama model error: {error}")
        return decoded

    @staticmethod
    def _extract_content(response_data: dict[str, Any]) -> str:
        message = response_data.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise InvalidStructuredOutputError(
                "Ollama response did not contain assistant content"
            )
        return content

    @staticmethod
    def _read_http_error(error: HTTPError) -> str:
        try:
            body = json.loads(error.read())
            message = body.get("error") if isinstance(body, dict) else None
            return f": {message}" if message else ""
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            return ""
