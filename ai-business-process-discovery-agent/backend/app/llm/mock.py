from copy import deepcopy
from typing import Any

from pydantic import BaseModel

from app.llm.base import LLMProvider, ResponseModelT
from app.llm.exceptions import InvalidStructuredOutputError


class MockLLMProvider(LLMProvider):
    """Deterministic, network-free provider configured with a test response."""

    def __init__(
        self,
        response: BaseModel | dict[str, Any] | str = "mock response",
        *,
        model_name: str = "deterministic-v1",
    ) -> None:
        self._response = response
        self._model_name = model_name
        self.requests: list[dict[str, Any]] = []

    @property
    def provider_name(self) -> str:
        return "mock"

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
        self.requests.append({
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        })
        response = deepcopy(self._response)
        if response_model is None:
            if isinstance(response, str):
                return response
            if isinstance(response, BaseModel):
                return response.model_dump_json()
            return str(response)
        try:
            if isinstance(response, BaseModel):
                return response_model.model_validate(response.model_dump())
            return response_model.model_validate(response)
        except Exception as exc:
            raise InvalidStructuredOutputError(
                "Mock response does not match the requested response model"
            ) from exc
