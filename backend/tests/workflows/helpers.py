from typing import Any

from app.llm import BusinessAnalysisResult, ProviderRequestError
from app.rag.context import AssembledContext, Citation
from app.rag.retrieval import RetrievalResponse
from app.rag.service import RAGResult
from app.rag.vector_store import SearchResult


def analysis_result(
    label: str,
    *,
    category: str = "process",
    severity: str = "medium",
    recommendation: str | None = None,
    evidence_source_ids: list[str] | None = None,
) -> BusinessAnalysisResult:
    return BusinessAnalysisResult.model_validate({
        "summary": f"{label} summary",
        "findings": [{
            "title": f"{label} finding",
            "description": f"Evidence-supported {label} description.",
            "category": category,
            "severity": severity,
            "evidence_source_ids": (
                ["Source 1"]
                if evidence_source_ids is None
                else evidence_source_ids
            ),
            "recommendation": recommendation or f"Review the {label}.",
        }],
        "assumptions": [],
        "insufficient_evidence": [],
        "confidence": 0.9,
    })


def rag_result(
    *,
    text: str = "Invoices require manager approval.",
    score: float = 0.9,
    document_id: str = "doc-1",
) -> RAGResult:
    if not text:
        return RAGResult(
            retrieval=RetrievalResponse(
                query="question",
                result_count=0,
                provider="fake",
                model="fake",
            ),
            context=AssembledContext(combined_context="", source_count=0),
        )
    search_result = SearchResult(
        chunk_id=f"chunk-{document_id}",
        document_id=document_id,
        text=text,
        score=score,
        chunk_index=0,
        metadata={"kind": "process", "project_id": "project-1"},
    )
    combined = f"[Source 1]\n{text}"
    return RAGResult(
        retrieval=RetrievalResponse(
            query="question",
            result_count=1,
            provider="fake",
            model="fake",
            results=[search_result],
        ),
        context=AssembledContext(
            combined_context=combined,
            citations=[
                Citation(
                    document_id,
                    search_result.chunk_id,
                    0,
                    score,
                    {"project_id": "project-1"},
                )
            ],
            source_count=1,
            character_count=len(combined),
        ),
    )


class FakeRAGService:
    def __init__(
        self,
        result: RAGResult | None = None,
        *,
        fail: bool = False,
        score: float = 0.9,
    ) -> None:
        self.result = result or rag_result(score=score)
        self.fail = fail
        self.score = score
        self.calls: list[dict[str, Any]] = []

    def query(self, query: str, **kwargs: Any) -> RAGResult:
        self.calls.append({"query": query, **kwargs})
        if self.fail:
            raise RuntimeError("sensitive retrieval detail")
        minimum = kwargs.get("minimum_score")
        if minimum is not None and self.score < minimum:
            return rag_result(text="")
        document_id = kwargs.get("document_id")
        if document_id:
            return rag_result(
                text=f"Evidence for {document_id}.",
                score=self.score,
                document_id=document_id,
            )
        return self.result


class FakeAnalysisService:
    def __init__(
        self,
        *,
        fail_on: int | None = None,
        responses: dict[int, BusinessAnalysisResult] | None = None,
    ) -> None:
        self.fail_on = fail_on
        self.responses = responses or {}
        self.calls: list[dict[str, Any]] = []

    def analyze(
        self, question: str, context_or_result: RAGResult
    ) -> BusinessAnalysisResult:
        index = len(self.calls)
        self.calls.append({
            "question": question,
            "context": context_or_result,
        })
        if self.fail_on == index:
            raise ProviderRequestError("sensitive provider detail")
        if index in self.responses:
            return self.responses[index]
        stage = index % 5
        if stage == 2:
            return analysis_result(f"analysis-{index}", category="risk")
        if stage == 3:
            return analysis_result(
                f"analysis-{index}",
                category="opportunity",
                recommendation="Use rule-based automation with human review.",
            )
        return analysis_result(f"analysis-{index}")


def workflow_input(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "project_id": "project-1",
        "question": "How does invoice approval work?",
        "document_id_filters": [],
        "metadata_filters": {"kind": "process"},
        "top_k": 5,
        "minimum_similarity_score": 0.5,
    }
    value.update(overrides)
    return value
