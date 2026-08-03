"""Application composition root.

Before this module existed, the RAG, LLM, LangGraph and X-Verba governance
layers were fully implemented but never constructed outside tests -- there
was no object graph tying them to the running FastAPI app. This module is
that missing wiring, and nothing else: it builds each collaborator exactly
once and hands it out. No business logic lives here.

Lifetimes are deliberate:
  * the vector store is process-wide, because retrieval must see chunks
    indexed by earlier requests;
  * the VerbaLedger is process-wide and file-backed, because a hash chain
    that restarts every request is not an audit trail;
  * the compiled graph is built once, because compiling gates per request
    would be wasteful and would not change behaviour.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from langgraph.graph.state import CompiledStateGraph
from vsl_core.ledger import JsonlLedgerStore, VerbaLedger

from app.core.config import settings
from app.document_processing import DocumentProcessor
from app.governance.process_discovery import (
    ProcessDiscoveryGovernanceConfig,
    ProcessDiscoveryGovernanceGates,
    ProcessDiscoveryGovernanceLedger,
    build_process_discovery_governance,
)
from app.llm import (
    AnalysisService,
    LLMProvider,
    MockLLMProvider,
    OllamaLLMProvider,
    OpenAILLMProvider,
)
from app.llm.models import BusinessAnalysisResult
from app.rag.chunking import DocumentChunker, ParagraphAwareChunker
from app.rag.context import ContextAssembler
from app.rag.embeddings import (
    DeterministicLocalEmbeddingProvider,
    EmbeddingProvider,
    EmbeddingService,
    OllamaEmbeddingProvider,
)
from app.rag.retrieval import SemanticRetriever
from app.rag.service import RAGService
from app.rag.vector_store import InMemoryVectorStore
from app.workflows.process_discovery import build_process_discovery_graph

logger = logging.getLogger(__name__)


class UnknownProviderError(ValueError):
    pass


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    provider = settings.embedding_provider.strip().lower()
    if provider == "ollama":
        logger.info("Using Ollama embeddings (%s)", settings.ollama_embedding_model)
        return OllamaEmbeddingProvider()
    if provider in {"local", "deterministic", ""}:
        return DeterministicLocalEmbeddingProvider(
            dimension=settings.local_embedding_dimension
        )
    raise UnknownProviderError(
        f"Unsupported EMBEDDING_PROVIDER {settings.embedding_provider!r}. "
        "Use 'local' or 'ollama'."
    )


@lru_cache
def get_vector_store() -> InMemoryVectorStore:
    return InMemoryVectorStore()


@lru_cache
def get_chunker() -> DocumentChunker:
    return ParagraphAwareChunker(
        chunk_size=settings.chunk_size,
        overlap=settings.chunk_overlap,
    )


@lru_cache
def get_document_processor() -> DocumentProcessor:
    return DocumentProcessor()


@lru_cache
def get_context_assembler() -> ContextAssembler:
    return ContextAssembler(max_characters=settings.max_context_characters)


@lru_cache
def get_rag_service() -> RAGService:
    provider = get_embedding_provider()
    store = get_vector_store()
    return RAGService(
        embedding_service=EmbeddingService(provider),
        embedding_provider=provider,
        vector_store=store,
        retriever=SemanticRetriever(provider, store),
        context_assembler=get_context_assembler(),
    )


@lru_cache
def get_llm_provider() -> LLMProvider:
    provider = settings.llm_provider.strip().lower()
    if provider == "ollama":
        return OllamaLLMProvider()
    if provider == "openai":
        return OpenAILLMProvider()
    if provider == "mock":
        # Only reachable when explicitly configured. Useful for smoke tests
        # and CI, never a silent fallback for a misconfigured provider.
        logger.warning("LLM_PROVIDER=mock: analyses will not be real.")
        return _StageAwareMockProvider()
    raise UnknownProviderError(
        f"Unsupported LLM_PROVIDER {settings.llm_provider!r}. "
        "Use 'ollama', 'openai' or 'mock'."
    )


@lru_cache
def get_analysis_service() -> AnalysisService:
    return AnalysisService(get_llm_provider())


@lru_cache
def get_verba_ledger() -> VerbaLedger:
    path = Path(settings.governance_ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return VerbaLedger(
        JsonlLedgerStore(path, fsync=settings.governance_ledger_fsync)
    )


@lru_cache
def get_governance_ledger() -> ProcessDiscoveryGovernanceLedger:
    return ProcessDiscoveryGovernanceLedger(get_verba_ledger())


@lru_cache
def get_governance_gates() -> ProcessDiscoveryGovernanceGates:
    return build_process_discovery_governance(
        ProcessDiscoveryGovernanceConfig(
            gamma_threshold=settings.governance_gamma_threshold,
            minimum_evidence_score=settings.governance_minimum_evidence_score,
            minimum_process_findings=settings.governance_minimum_process_findings,
        )
    )


@lru_cache
def get_process_discovery_graph() -> CompiledStateGraph:
    return build_process_discovery_graph(
        rag_service=get_rag_service(),
        analysis_service=get_analysis_service(),
        governance_gates=get_governance_gates(),
        governance_ledger=get_governance_ledger(),
    )


class _StageAwareMockProvider(MockLLMProvider):
    """A mock whose shape changes per workflow stage.

    A single fixed response cannot pass the workflow: `risk_scope_invariant`
    requires a risk-category finding and `automation_safety_invariant`
    requires a human-review commitment, so a one-size response is denied
    partway through and `LLM_PROVIDER=mock` would be useless as a smoke
    test. This returns a stage-appropriate, invariant-satisfying result so
    the full governed path can be exercised without a live model.

    It is still a mock. It reads no evidence and its findings mean nothing.
    """

    _STAGES: tuple[tuple[str, str, str, str], ...] = (
        (
            "Focus only on discovering the process",
            "process",
            "Mock process step",
            "Review this step with the process owner.",
        ),
        (
            "Focus only on evidence-supported bottlenecks",
            "bottleneck",
            "Mock bottleneck",
            "Measure the wait time at this step before acting.",
        ),
        (
            "Focus only on evidence-supported operational and control risks",
            "risk",
            "Mock control risk",
            "Confirm the control owner and evidence retention.",
        ),
        (
            "Focus only on evidence-supported automation opportunities",
            "opportunity",
            "Mock automation opportunity",
            "Pilot rule-based automation with human review before rollout.",
        ),
    )

    @property
    def provider_name(self) -> str:
        return "mock"

    def generate(  # type: ignore[override]
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        response_model=None,
        temperature=None,
        max_output_tokens=None,
    ):
        category, title, recommendation = "process", "Mock synthesis", (
            "Validate every finding with the process owner before acting."
        )
        for marker, stage_category, stage_title, stage_recommendation in self._STAGES:
            if marker in user_prompt:
                category = stage_category
                title = stage_title
                recommendation = stage_recommendation
                break

        result = BusinessAnalysisResult.model_validate({
            "summary": (
                "Deterministic mock analysis produced without reading the "
                "evidence. Not a real result."
            ),
            "findings": [{
                "title": title,
                "description": (
                    "Placeholder finding emitted by MockLLMProvider so the "
                    "governed workflow can be exercised offline."
                ),
                "category": category,
                "severity": "medium",
                "evidence_source_ids": _first_source_ids(user_prompt),
                "recommendation": recommendation,
            }],
            "assumptions": [{
                "description": "The mock provider did not read the evidence.",
                "reason": "LLM_PROVIDER is set to 'mock'.",
            }],
            "insufficient_evidence": [
                "Every element, because no model was called.",
            ],
            "confidence": 0.1,
        })
        if response_model is None:
            return result.model_dump_json()
        return response_model.model_validate(result.model_dump())


def _first_source_ids(user_prompt: str) -> list[str]:
    """Cite only markers actually present, or the invariant denies us."""
    import re

    numbers = re.findall(r"\[Source (\d+)\]", user_prompt)
    return [f"Source {numbers[0]}"] if numbers else []


def reset_composition() -> None:
    """Clear every cached collaborator. Used by tests only."""
    for factory in (
        get_embedding_provider,
        get_vector_store,
        get_chunker,
        get_document_processor,
        get_context_assembler,
        get_rag_service,
        get_llm_provider,
        get_analysis_service,
        get_verba_ledger,
        get_governance_ledger,
        get_governance_gates,
        get_process_discovery_graph,
    ):
        # Tolerate factories a test has monkeypatched over.
        clear = getattr(factory, "cache_clear", None)
        if clear is not None:
            clear()
