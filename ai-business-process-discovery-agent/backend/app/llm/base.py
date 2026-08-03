from abc import ABC, abstractmethod
from typing import TypeVar, overload

from pydantic import BaseModel

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)


class LLMProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the stable provider name."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the provider-specific model name."""

    @overload
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        response_model: type[ResponseModelT],
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> ResponseModelT: ...

    @overload
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        response_model: None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> str: ...

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        response_model: type[ResponseModelT] | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> ResponseModelT | str:
        """Generate text or a validated Pydantic response."""
