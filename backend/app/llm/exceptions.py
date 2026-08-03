class LLMError(Exception):
    """Base exception for the LLM integration layer."""


class EmptyQuestionError(LLMError, ValueError):
    """Raised when an analysis question is blank."""


class EmptyContextError(LLMError, ValueError):
    """Raised when no usable retrieved evidence is available."""


class InvalidStructuredOutputError(LLMError, ValueError):
    """Raised when a provider response does not match the response contract."""


class ProviderUnavailableError(LLMError):
    """Raised when a configured provider cannot be used."""


class ProviderRequestError(LLMError):
    """Raised when a provider request fails."""
