from typing import Any

from pydantic import ValidationError

from app.core.config import settings
from app.llm.base import LLMProvider, ResponseModelT
from app.llm.exceptions import (
    InvalidStructuredOutputError,
    ProviderRequestError,
    ProviderUnavailableError,
)


class OpenAILLMProvider(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
    ) -> None:
        resolved_api_key = api_key or settings.openai_api_key
        resolved_model_name = model_name or settings.openai_model
        if not resolved_api_key or not resolved_api_key.strip():
            raise ProviderUnavailableError(
                "OPENAI_API_KEY is required when the OpenAI provider is selected"
            )
        if not resolved_model_name.strip():
            raise ProviderUnavailableError("OPENAI_MODEL must not be empty")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderUnavailableError(
                "The OpenAI Python package is not installed"
            ) from exc
        self._client: Any = OpenAI(api_key=resolved_api_key)
        self._model_name = resolved_model_name

    @property
    def provider_name(self) -> str:
        return "openai"

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
        request: dict[str, Any] = {
            "model": self.model_name,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if temperature is not None:
            request["temperature"] = temperature
        if max_output_tokens is not None:
            request["max_output_tokens"] = max_output_tokens
        try:
            if response_model is not None:
                response = self._client.responses.parse(
                    **request, text_format=response_model
                )
                parsed = response.output_parsed
                if parsed is None:
                    raise InvalidStructuredOutputError(
                        "OpenAI returned no parsed structured output"
                    )
                return response_model.model_validate(parsed)
            response = self._client.responses.create(**request)
            return response.output_text
        except InvalidStructuredOutputError:
            raise
        except ValidationError as exc:
            raise InvalidStructuredOutputError(
                "OpenAI response did not match the requested response model"
            ) from exc
        except Exception as exc:
            raise ProviderRequestError("OpenAI request failed") from exc
