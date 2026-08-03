import pytest

from app.llm import (
    AnalysisService,
    BusinessAnalysisResult,
    EmptyContextError,
    EmptyQuestionError,
    InvalidStructuredOutputError,
    LLMProvider,
    MockLLMProvider,
    PromptBuilder,
    PromptRequest,
    ProviderRequestError,
)
from app.rag.context import AssembledContext, Citation
from app.rag.retrieval import RetrievalResponse
from app.rag.service import RAGResult


def context() -> AssembledContext:
    text = (
        "[Source 1]\nInvoices require manager approval.\n\n"
        "[Source 2]\nThe finance team enters approved invoices manually."
    )
    return AssembledContext(
        combined_context=text,
        citations=[
            Citation("doc-1", "chunk-1", 0, 0.97),
            Citation("doc-2", "chunk-2", 3, 0.88),
        ],
        source_count=2,
        character_count=len(text),
    )


def response() -> dict[str, object]:
    return {
        "summary": "The process uses approval followed by manual entry.",
        "findings": [{
            "title": "Manual finance entry",
            "description": "Finance manually enters approved invoices.",
            "category": "bottleneck",
            "severity": "medium",
            "evidence_source_ids": ["Source 2"],
            "recommendation": "Assess whether entry can be automated.",
        }],
        "assumptions": [{
            "description": "Manual entry may add processing time.",
            "reason": "No cycle-time measurements were supplied.",
        }],
        "insufficient_evidence": ["No processing-time data was supplied."],
        "confidence": 0.82,
    }


def test_prompt_contains_question_evidence_and_source_markers() -> None:
    package = PromptBuilder().build(
        PromptRequest(question="Where are the delays?", context=context())
    )
    assert "senior business process consultant" in package.system.content
    assert "Where are the delays?" in package.user.content
    assert "Invoices require manager approval." in package.user.content
    assert "[Source 1]" in package.user.content
    assert "[Source 2]" in package.user.content


def test_prompt_contains_grounding_and_structured_output_instructions() -> None:
    package = PromptBuilder().build(
        PromptRequest(question="What happens?", context=context())
    )
    system = package.system.content.lower()
    assert "only the supplied evidence" in system
    assert "do not invent missing facts" in system
    assert "evidence is insufficient" in system
    assert "separate evidence-based findings from assumptions" in system
    assert "do not make legal" in system
    assert "structured response" in system
    assert "evidence_source_ids" in system


def test_mock_provider_returns_structured_grounded_analysis() -> None:
    provider = MockLLMProvider(response(), model_name="mock-analysis-v1")
    result = AnalysisService(
        provider, temperature=0.1, max_output_tokens=700
    ).analyze("Where are the delays?", context())

    assert isinstance(result, BusinessAnalysisResult)
    assert result.findings[0].evidence_source_ids == ["Source 2"]
    assert result.assumptions[0].description.startswith("Manual entry")
    assert result.insufficient_evidence == [
        "No processing-time data was supplied."
    ]
    assert result.provider_name == "mock"
    assert result.model_name == "mock-analysis-v1"
    assert provider.requests[0]["temperature"] == 0.1
    assert provider.requests[0]["max_output_tokens"] == 700


def test_service_accepts_rag_result() -> None:
    assembled = context()
    rag_result = RAGResult(
        retrieval=RetrievalResponse(
            query="Where are the delays?",
            result_count=0,
            provider="test",
            model="test",
        ),
        context=assembled,
    )
    result = AnalysisService(MockLLMProvider(response())).analyze(
        "Where are the delays?", rag_result
    )
    assert result.findings[0].evidence_source_ids == ["Source 2"]


@pytest.mark.parametrize("question", ["", " ", "\n\t"])
def test_empty_question_is_rejected(question: str) -> None:
    with pytest.raises(EmptyQuestionError, match="must not be empty"):
        AnalysisService(MockLLMProvider(response())).analyze(question, context())


def test_empty_context_is_rejected_before_provider_call() -> None:
    provider = MockLLMProvider(response())
    with pytest.raises(EmptyContextError, match="must not be empty"):
        AnalysisService(provider).analyze(
            "What happens?",
            AssembledContext(combined_context="", source_count=0),
        )
    assert provider.requests == []


class FailingProvider(LLMProvider):
    provider_name = "failing"
    model_name = "failure-v1"

    def generate(self, *args: object, **kwargs: object) -> str:
        raise RuntimeError("provider is down")


def test_provider_failure_is_mapped_without_leaking_provider_error() -> None:
    with pytest.raises(ProviderRequestError, match="provider request failed"):
        AnalysisService(FailingProvider()).analyze("What happens?", context())


def test_invalid_structured_response_is_rejected() -> None:
    with pytest.raises(InvalidStructuredOutputError, match="Mock response"):
        AnalysisService(MockLLMProvider({"summary": "incomplete"})).analyze(
            "What happens?", context()
        )


def test_unknown_source_identifier_is_rejected() -> None:
    invalid = response()
    invalid["findings"][0]["evidence_source_ids"] = ["Source 99"]  # type: ignore[index]
    with pytest.raises(InvalidStructuredOutputError, match="Source 99"):
        AnalysisService(MockLLMProvider(invalid)).analyze(
            "What happens?", context()
        )


def test_mock_text_generation_and_metadata_are_deterministic() -> None:
    provider = MockLLMProvider("fixed", model_name="fixture-v2")
    assert provider.generate("system", "user") == "fixed"
    assert provider.generate("system", "different user") == "fixed"
    assert provider.provider_name == "mock"
    assert provider.model_name == "fixture-v2"
