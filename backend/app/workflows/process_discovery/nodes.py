import logging
import math
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from vsl_core.exceptions import AutomationDeniedException

from app.governance.process_discovery.ledger import (
    ProcessDiscoveryGovernanceLedger,
)
from app.governance.process_discovery.models import (
    GovernanceStage,
    GovernanceStatus,
)
from app.llm.exceptions import LLMError
from app.llm.models import BusinessAnalysisResult
from app.llm.service import AnalysisService
from app.rag.context import ContextAssembler
from app.rag.retrieval import RetrievalResponse
from app.rag.service import RAGResult, RAGService
from app.rag.vector_store import SearchResult
from app.workflows.process_discovery.exceptions import WorkflowValidationError
from app.workflows.process_discovery.models import WorkflowStage, WorkflowStatus
from app.workflows.process_discovery.state import ProcessDiscoveryState

logger = logging.getLogger(__name__)

Clock = Callable[[], datetime]
IdFactory = Callable[[], str]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProcessDiscoveryNodes:
    """Small workflow nodes bound only to injected application services."""

    def __init__(
        self,
        rag_service: RAGService,
        analysis_service: AnalysisService,
        governance_ledger: ProcessDiscoveryGovernanceLedger,
        *,
        clock: Clock = _utc_now,
        id_factory: IdFactory = lambda: str(uuid.uuid4()),
    ) -> None:
        self._rag_service = rag_service
        self._analysis_service = analysis_service
        self._governance_ledger = governance_ledger
        self._clock = clock
        self._id_factory = id_factory

    def validate_input(
        self, state: ProcessDiscoveryState
    ) -> ProcessDiscoveryState:
        errors = list(state.get("errors", []))
        if state.get("terminal_state_name") is not None:
            return {
                "status": state.get(
                    "status", WorkflowStatus.GOVERNANCE_BLOCKED
                ),
                "current_stage": state.get(
                    "current_stage", WorkflowStage.GOVERNANCE_BLOCKED
                ),
                "errors": [
                    *errors,
                    "A terminal workflow instance cannot be automatically restarted.",
                ],
                "completed_at": state.get("completed_at") or self._clock(),
            }
        workflow_id = state.get("workflow_id") or self._id_factory()
        update: ProcessDiscoveryState = {
            "workflow_id": workflow_id,
            "document_id_filters": [],
            "metadata_filters": dict(state.get("metadata_filters") or {}),
            "top_k": state.get("top_k", 5),
            "minimum_similarity_score": state.get(
                "minimum_similarity_score"
            ),
            "rag_result": None,
            "process_analysis": None,
            "bottleneck_analysis": None,
            "risk_analysis": None,
            "automation_analysis": None,
            "final_analysis": None,
            "current_stage": WorkflowStage.VALIDATION,
            "status": WorkflowStatus.RUNNING,
            "errors": errors,
            "started_at": self._clock(),
            "completed_at": None,
            "governance_status": GovernanceStatus.MONITORING,
            "governance_stage": GovernanceStage.VALIDATION,
            "vsl_denial": None,
            "denial_summary": None,
            "terminal_state_name": None,
            "governance_decisions": [],
            "human_review_required": False,
            "governance_instance_id": (
                state.get("governance_instance_id")
                or f"process-discovery:{workflow_id}"
            ),
        }
        try:
            project_id = str(state.get("project_id", "")).strip()
            question = str(state.get("question", "")).strip()
            top_k = state.get("top_k", 5)
            minimum_score = state.get("minimum_similarity_score")
            if not project_id:
                raise WorkflowValidationError("project_id must not be empty")
            if not question:
                raise WorkflowValidationError("question must not be empty")
            if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
                raise WorkflowValidationError("top_k must be a positive integer")
            if minimum_score is not None and (
                not isinstance(minimum_score, (int, float))
                or isinstance(minimum_score, bool)
                or not math.isfinite(minimum_score)
                or not -1.0 <= minimum_score <= 1.0
            ):
                raise WorkflowValidationError(
                    "minimum_similarity_score must be between -1 and 1"
                )
            filters = state.get("document_id_filters") or []
            if not isinstance(filters, list):
                raise WorkflowValidationError(
                    "document_id_filters must be a list"
                )
            document_ids = list(dict.fromkeys(
                item.strip()
                for item in filters
                if isinstance(item, str) and item.strip()
            ))
            if len(document_ids) != len(filters):
                raise WorkflowValidationError(
                    "document_id_filters must contain unique non-empty strings"
                )
            metadata = state.get("metadata_filters") or {}
            if not isinstance(metadata, dict):
                raise WorkflowValidationError("metadata_filters must be a mapping")
        except WorkflowValidationError as exc:
            errors.append(f"Input validation failed: {exc}")
            update.update({
                "status": WorkflowStatus.FAILED,
                "errors": errors,
            })
            return update

        update.update({
            "project_id": project_id,
            "question": question,
            "document_id_filters": document_ids,
            "metadata_filters": dict(metadata),
            "top_k": top_k,
            "minimum_similarity_score": (
                float(minimum_score) if minimum_score is not None else None
            ),
        })
        return update

    def retrieve_evidence(
        self, state: ProcessDiscoveryState
    ) -> ProcessDiscoveryState:
        try:
            rag_result = self._retrieve(state)
        except Exception:
            logger.exception(
                "Evidence retrieval failed for workflow %s",
                state.get("workflow_id", "unknown"),
            )
            return self._failed_update(
                state,
                "Evidence retrieval failed. No analysis was performed.",
            )

        if (
            rag_result.retrieval.result_count == 0
            or rag_result.context.source_count == 0
            or not rag_result.context.combined_context.strip()
        ):
            return {
                "rag_result": rag_result,
                "current_stage": WorkflowStage.RETRIEVAL,
                "status": WorkflowStatus.INSUFFICIENT_EVIDENCE,
            }
        return {
            "rag_result": rag_result,
            "current_stage": WorkflowStage.RETRIEVAL,
            "status": WorkflowStatus.RUNNING,
        }

    def discover_process(
        self, state: ProcessDiscoveryState
    ) -> ProcessDiscoveryState:
        instruction = (
            f"{state['question']}\n\n"
            "Focus only on discovering the process: identify its trigger, ordered "
            "steps, actors or roles, systems, decisions, handoffs, inputs, and "
            "outputs. State explicitly which elements lack evidence."
        )
        return self._run_analysis(
            state,
            instruction,
            result_key="process_analysis",
            stage=WorkflowStage.PROCESS_DISCOVERY,
            failure_label="Process discovery",
        )

    def analyse_bottlenecks(
        self, state: ProcessDiscoveryState
    ) -> ProcessDiscoveryState:
        prior = self._analysis_json(state.get("process_analysis"))
        instruction = (
            f"{state['question']}\n\n"
            "Focus only on evidence-supported bottlenecks: waiting time, manual "
            "handoffs, duplicated activities, repeated approvals, rework loops, "
            "and system switching. Use the prior process analysis only as a "
            f"navigation aid and verify claims against evidence.\nPrior analysis: {prior}"
        )
        return self._run_analysis(
            state,
            instruction,
            result_key="bottleneck_analysis",
            stage=WorkflowStage.BOTTLENECK_ANALYSIS,
            failure_label="Bottleneck analysis",
        )

    def analyse_risks(
        self, state: ProcessDiscoveryState
    ) -> ProcessDiscoveryState:
        prior = self._analysis_json(state.get("process_analysis"))
        instruction = (
            f"{state['question']}\n\n"
            "Focus only on evidence-supported operational and control risks. Flag "
            "possible policy, privacy, access, audit, and segregation-of-duty "
            "concerns without making legal, regulatory, or compliance conclusions. "
            "Separate possible concerns from established evidence."
            f"\nPrior process analysis: {prior}"
        )
        return self._run_analysis(
            state,
            instruction,
            result_key="risk_analysis",
            stage=WorkflowStage.RISK_ANALYSIS,
            failure_label="Risk analysis",
        )

    def analyse_automation(
        self, state: ProcessDiscoveryState
    ) -> ProcessDiscoveryState:
        prior = self._analysis_json(state.get("process_analysis"))
        bottlenecks = self._analysis_json(state.get("bottleneck_analysis"))
        instruction = (
            f"{state['question']}\n\n"
            "Focus only on evidence-supported automation opportunities. "
            "Distinguish rule-based automation, system integration, AI-assisted "
            "work, human-dependent work, and unsuitable-for-automation activities. "
            "Include human-review requirements where appropriate."
            f"\nPrior process analysis: {prior}"
            f"\nPrior bottleneck analysis: {bottlenecks}"
        )
        return self._run_analysis(
            state,
            instruction,
            result_key="automation_analysis",
            stage=WorkflowStage.AUTOMATION_ANALYSIS,
            failure_label="Automation analysis",
        )

    def synthesise_results(
        self, state: ProcessDiscoveryState
    ) -> ProcessDiscoveryState:
        instruction = (
            f"{state['question']}\n\n"
            "Synthesize one final business-process analysis from the focused "
            "analyses below. Resolve overlaps, preserve source identifiers, use "
            "only claims grounded in the retrieved evidence, and do not invent "
            "facts. Keep assumptions and insufficient evidence explicit."
            f"\nProcess analysis: {self._analysis_json(state.get('process_analysis'))}"
            "\nBottleneck analysis: "
            f"{self._analysis_json(state.get('bottleneck_analysis'))}"
            f"\nRisk analysis: {self._analysis_json(state.get('risk_analysis'))}"
            "\nAutomation analysis: "
            f"{self._analysis_json(state.get('automation_analysis'))}"
        )
        return self._run_analysis(
            state,
            instruction,
            result_key="final_analysis",
            stage=WorkflowStage.FINAL_SYNTHESIS,
            failure_label="Final synthesis",
        )

    def complete_workflow(
        self, state: ProcessDiscoveryState
    ) -> ProcessDiscoveryState:
        return {
            "status": WorkflowStatus.COMPLETED,
            "current_stage": WorkflowStage.COMPLETED,
            "completed_at": self._clock(),
            "governance_status": GovernanceStatus.ALLOWED,
        }

    def fail_workflow(
        self, state: ProcessDiscoveryState
    ) -> ProcessDiscoveryState:
        return {
            "status": WorkflowStatus.FAILED,
            "current_stage": WorkflowStage.FAILED,
            "errors": list(state.get("errors", [])),
            "completed_at": self._clock(),
        }

    def insufficient_evidence(
        self, state: ProcessDiscoveryState
    ) -> ProcessDiscoveryState:
        try:
            decision = self._governance_ledger.record_insufficient_evidence(state)
        except Exception:
            logger.exception(
                "Unable to record insufficient-evidence terminal for workflow %s",
                state.get("workflow_id", "unknown"),
            )
            return self._failed_update(
                state,
                "Governance ledger recording failed.",
            )
        return {
            "status": WorkflowStatus.INSUFFICIENT_EVIDENCE,
            "current_stage": WorkflowStage.RETRIEVAL,
            "process_analysis": None,
            "bottleneck_analysis": None,
            "risk_analysis": None,
            "automation_analysis": None,
            "final_analysis": None,
            "completed_at": self._clock(),
            "governance_status": GovernanceStatus.BLOCKED,
            "governance_stage": GovernanceStage.TERMINAL,
            "terminal_state_name": "INSUFFICIENT_EVIDENCE",
            "governance_decisions": [
                *state.get("governance_decisions", []),
                decision,
            ],
        }

    def governance_blocked(
        self, state: ProcessDiscoveryState
    ) -> ProcessDiscoveryState:
        denial = state.get("vsl_denial")
        if not isinstance(denial, AutomationDeniedException):
            return self._failed_update(
                state,
                "Governance routing failed without a valid denial.",
            )
        try:
            decision, summary = self._governance_ledger.record_denial(
                state, denial
            )
        except Exception:
            logger.exception(
                "Unable to record governance denial for workflow %s",
                state.get("workflow_id", "unknown"),
            )
            return self._failed_update(
                state,
                "Governance ledger recording failed.",
            )
        human_review = bool(summary["human_review_required"])
        return {
            "status": (
                WorkflowStatus.HUMAN_REVIEW_REQUIRED
                if human_review
                else WorkflowStatus.GOVERNANCE_BLOCKED
            ),
            "current_stage": (
                WorkflowStage.HUMAN_REVIEW_REQUIRED
                if human_review
                else WorkflowStage.GOVERNANCE_BLOCKED
            ),
            "governance_status": (
                GovernanceStatus.HUMAN_REVIEW_REQUIRED
                if human_review
                else GovernanceStatus.BLOCKED
            ),
            "governance_stage": GovernanceStage.TERMINAL,
            "denial_summary": summary,
            "terminal_state_name": summary["terminal_state_name"],
            "human_review_required": human_review,
            "governance_decisions": [
                *state.get("governance_decisions", []),
                decision,
            ],
            "completed_at": self._clock(),
        }

    def _retrieve(self, state: ProcessDiscoveryState) -> RAGResult:
        document_ids = state.get("document_id_filters", [])
        common: dict[str, Any] = {
            "top_k": state["top_k"],
            "metadata_filters": state.get("metadata_filters", {}),
            "minimum_score": state.get("minimum_similarity_score"),
        }
        if len(document_ids) <= 1:
            return self._rag_service.query(
                state["question"],
                document_id=document_ids[0] if document_ids else None,
                **common,
            )

        results: list[SearchResult] = []
        first_result: RAGResult | None = None
        for document_id in document_ids:
            current = self._rag_service.query(
                state["question"],
                document_id=document_id,
                **common,
            )
            first_result = first_result or current
            results.extend(current.retrieval.results)

        unique_results: list[SearchResult] = []
        seen_chunks: set[str] = set()
        for result in sorted(results, key=lambda item: item.score, reverse=True):
            if result.chunk_id not in seen_chunks:
                seen_chunks.add(result.chunk_id)
                unique_results.append(result)
            if len(unique_results) == state["top_k"]:
                break

        assert first_result is not None
        retrieval = RetrievalResponse(
            query=state["question"],
            result_count=len(unique_results),
            provider=first_result.retrieval.provider,
            model=first_result.retrieval.model,
            results=unique_results,
        )
        return RAGResult(
            retrieval=retrieval,
            context=ContextAssembler().assemble(unique_results),
        )

    def _run_analysis(
        self,
        state: ProcessDiscoveryState,
        instruction: str,
        *,
        result_key: str,
        stage: WorkflowStage,
        failure_label: str,
    ) -> ProcessDiscoveryState:
        rag_result = state.get("rag_result")
        if rag_result is None:
            return self._failed_update(
                state,
                f"{failure_label} failed because retrieved evidence was unavailable.",
            )
        try:
            result = self._analysis_service.analyze(instruction, rag_result)
        except LLMError:
            logger.warning(
                "%s failed for workflow %s",
                failure_label,
                state.get("workflow_id", "unknown"),
                exc_info=True,
            )
            return self._failed_update(
                state,
                f"{failure_label} failed because the analysis provider was unavailable.",
            )
        except Exception:
            logger.exception(
                "%s failed for workflow %s",
                failure_label,
                state.get("workflow_id", "unknown"),
            )
            return self._failed_update(
                state,
                f"{failure_label} failed due to an internal analysis error.",
            )
        return {
            result_key: result,  # type: ignore[typeddict-item]
            "current_stage": stage,
            "status": WorkflowStatus.RUNNING,
        }

    @staticmethod
    def _failed_update(
        state: ProcessDiscoveryState, message: str
    ) -> ProcessDiscoveryState:
        return {
            "status": WorkflowStatus.FAILED,
            "current_stage": WorkflowStage.FAILED,
            "errors": [*state.get("errors", []), message],
        }

    @staticmethod
    def _analysis_json(result: BusinessAnalysisResult | None) -> str:
        if result is None:
            return "not available"
        return result.model_dump_json(
            exclude={"provider_name", "model_name"},
            exclude_none=True,
        )
