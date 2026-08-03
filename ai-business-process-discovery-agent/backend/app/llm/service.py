import re

from pydantic import ValidationError

from app.core.config import settings
from app.llm.base import LLMProvider
from app.llm.exceptions import (
    EmptyContextError,
    EmptyQuestionError,
    InvalidStructuredOutputError,
    LLMError,
    ProviderRequestError,
)
from app.llm.models import BusinessAnalysisResult
from app.llm.prompts import PromptBuilder, PromptRequest
from app.rag.context import AssembledContext
from app.rag.service import RAGResult


class AnalysisService:
    def __init__(
        self,
        provider: LLMProvider,
        prompt_builder: PromptBuilder | None = None,
        *,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> None:
        self._provider = provider
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._temperature = (
            settings.llm_temperature if temperature is None else temperature
        )
        self._max_output_tokens = (
            settings.llm_max_output_tokens
            if max_output_tokens is None
            else max_output_tokens
        )

    def analyze(
        self,
        question: str,
        context_or_result: AssembledContext | RAGResult,
    ) -> BusinessAnalysisResult:
        if not question or not question.strip():
            raise EmptyQuestionError("Business question must not be empty")
        context = (
            context_or_result.context
            if isinstance(context_or_result, RAGResult)
            else context_or_result
        )
        if not isinstance(context, AssembledContext):
            raise EmptyContextError("A valid assembled context is required")
        if not context.combined_context.strip() or context.source_count < 1:
            raise EmptyContextError("Retrieved context must not be empty")

        package = self._prompt_builder.build(
            PromptRequest(question=question.strip(), context=context)
        )
        try:
            raw_result = self._provider.generate(
                package.system.content,
                package.user.content,
                response_model=BusinessAnalysisResult,
                temperature=self._temperature,
                max_output_tokens=self._max_output_tokens,
            )
            result = BusinessAnalysisResult.model_validate(raw_result)
            self._validate_source_ids(result, context)
        except (InvalidStructuredOutputError, ProviderRequestError):
            raise
        except ValidationError as exc:
            raise InvalidStructuredOutputError(
                "Provider response is not a valid BusinessAnalysisResult"
            ) from exc
        except LLMError:
            raise
        except Exception as exc:
            raise ProviderRequestError("LLM provider request failed") from exc

        return result.model_copy(update={
            "provider_name": self._provider.provider_name,
            "model_name": self._provider.model_name,
        })

    def analyse(
        self,
        question: str,
        context_or_result: AssembledContext | RAGResult,
    ) -> BusinessAnalysisResult:
        """British-English alias retained for application terminology."""
        return self.analyze(question, context_or_result)

    @staticmethod
    def _validate_source_ids(
        result: BusinessAnalysisResult, context: AssembledContext
    ) -> None:
        available = {
            f"Source {number}"
            for number in re.findall(r"\[Source (\d+)\]", context.combined_context)
        }
        referenced = {
            source_id.removeprefix("[").removesuffix("]")
            for finding in result.findings
            for source_id in finding.evidence_source_ids
        }
        unknown = referenced - available
        if unknown:
            raise InvalidStructuredOutputError(
                "Provider referenced unknown evidence sources: "
                + ", ".join(sorted(unknown))
            )
