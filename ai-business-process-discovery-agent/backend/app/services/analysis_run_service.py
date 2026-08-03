"""Run the governed process-discovery graph and persist what it produced.

The LangGraph graph is asynchronous because `vsl_langgraph.gated_node` is
asynchronous, so it must be driven with `ainvoke`. It is executed as a
background task: five sequential LLM calls take minutes, which is far too
long to hold an HTTP request open.

Only safe metadata is persisted from governance. Document text, prompts,
embeddings, provider exceptions and stack traces are deliberately excluded,
matching the guarantee documented in `docs/vsl-native-process-discovery.md`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.composition import (
    get_process_discovery_graph,
    get_verba_ledger,
)
from app.core.config import settings
from app.models.analysis import AnalysisRun, GovernanceEvent, LedgerEntryRecord
from app.models.document import Document, DocumentIndexStatus
from app.models.project import Project
from app.workflows.process_discovery import WorkflowStage, WorkflowStatus

logger = logging.getLogger(__name__)


class ProjectNotFoundError(LookupError):
    pass


class AnalysisRunNotFoundError(LookupError):
    pass


class NoIndexedEvidenceError(ValueError):
    """Raised before starting a run that could only ever fail."""


class AnalysisRunService:
    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Creation -----------------------------------------------------

    def create_run(
        self,
        project_id: str,
        *,
        question: str,
        top_k: int | None = None,
        minimum_similarity_score: float | None = None,
        document_id_filters: list[str] | None = None,
    ) -> AnalysisRun:
        project = self._session.get(Project, project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)

        indexed = self._session.execute(
            select(Document.id)
            .where(Document.project_id == project_id)
            .where(Document.index_status == DocumentIndexStatus.INDEXED.value)
        ).scalars().all()
        if not indexed:
            raise NoIndexedEvidenceError(
                "This project has no successfully indexed documents. Upload a "
                "document and wait for indexing to finish before running an "
                "analysis."
            )

        requested = list(dict.fromkeys(document_id_filters or []))
        unknown = [document_id for document_id in requested if document_id not in indexed]
        if unknown:
            raise NoIndexedEvidenceError(
                "These documents are not indexed and cannot be analysed: "
                + ", ".join(unknown)
            )

        run = AnalysisRun(
            project_id=project_id,
            question=question.strip(),
            top_k=top_k if top_k is not None else settings.retrieval_top_k,
            minimum_similarity_score=minimum_similarity_score,
            document_id_filters=requested,
            # Scoping retrieval by project is what keeps the governance
            # monitors' `project_id` check satisfiable.
            metadata_filters={"project_id": project_id},
            status=WorkflowStatus.PENDING.value,
            current_stage=WorkflowStage.VALIDATION.value,
        )
        self._session.add(run)
        self._session.commit()
        self._session.refresh(run)
        return run

    # --- Execution ----------------------------------------------------

    async def execute_run(self, run_id: str) -> None:
        """Drive the governed graph. Never raises."""
        run = self._session.get(AnalysisRun, run_id)
        if run is None:
            logger.warning("Cannot execute unknown analysis run %s", run_id)
            return

        run.status = WorkflowStatus.RUNNING.value
        run.started_at = datetime.now(timezone.utc)
        self._session.commit()

        ledger_start = self._ledger_length()

        try:
            graph = get_process_discovery_graph()
            state = await graph.ainvoke({
                "project_id": run.project_id,
                "question": run.question,
                "document_id_filters": list(run.document_id_filters or []),
                "metadata_filters": dict(run.metadata_filters or {}),
                "top_k": run.top_k,
                "minimum_similarity_score": run.minimum_similarity_score,
            })
        except Exception:
            logger.exception("Analysis run %s crashed", run_id)
            run.status = WorkflowStatus.FAILED.value
            run.current_stage = WorkflowStage.FAILED.value
            run.errors = [
                *(run.errors or []),
                "The analysis workflow failed unexpectedly. Check the server "
                "logs for detail.",
            ]
            run.completed_at = datetime.now(timezone.utc)
            self._session.commit()
            return

        self._apply_state(run, state)
        self._persist_ledger_entries(run, ledger_start)
        self._session.commit()
        logger.info("Analysis run %s finished with status %s", run_id, run.status)

    # --- Reads --------------------------------------------------------

    def list_runs(self, project_id: str) -> list[AnalysisRun]:
        if self._session.get(Project, project_id) is None:
            raise ProjectNotFoundError(project_id)
        return list(
            self._session.execute(
                select(AnalysisRun)
                .where(AnalysisRun.project_id == project_id)
                .order_by(AnalysisRun.created_at.desc())
            ).scalars()
        )

    def get_run(self, run_id: str) -> AnalysisRun:
        run = self._session.get(AnalysisRun, run_id)
        if run is None:
            raise AnalysisRunNotFoundError(run_id)
        return run

    # --- Internals ----------------------------------------------------

    def _apply_state(self, run: AnalysisRun, state: dict[str, Any]) -> None:
        run.workflow_id = _text(state.get("workflow_id"))
        run.governance_instance_id = _text(state.get("governance_instance_id"))
        run.status = _enum_value(state.get("status"), WorkflowStatus.FAILED.value)
        run.current_stage = _enum_value(
            state.get("current_stage"), WorkflowStage.FAILED.value
        )
        run.governance_status = _enum_value(state.get("governance_status"), "pending")
        run.governance_stage = _enum_value(state.get("governance_stage"), "validation")
        run.terminal_state_name = _text(state.get("terminal_state_name"))
        run.human_review_required = bool(state.get("human_review_required", False))
        run.denial_summary = state.get("denial_summary")
        run.errors = list(state.get("errors", []) or [])

        for key in (
            "process_analysis",
            "bottleneck_analysis",
            "risk_analysis",
            "automation_analysis",
            "final_analysis",
        ):
            analysis = state.get(key)
            setattr(
                run,
                key,
                analysis.model_dump(mode="json") if analysis is not None else None,
            )

        rag_result = state.get("rag_result")
        if rag_result is not None:
            context = rag_result.context
            run.citations = [
                {
                    "source_id": f"Source {index}",
                    "document_id": citation.document_id,
                    "chunk_id": citation.chunk_id,
                    "chunk_index": citation.chunk_index,
                    "score": citation.score,
                    "filename": citation.metadata.get("filename"),
                }
                for index, citation in enumerate(context.citations, start=1)
            ]
            run.retrieval_provider = rag_result.retrieval.provider
            run.retrieval_model = rag_result.retrieval.model
            run.retrieved_count = rag_result.retrieval.result_count
            run.source_count = context.source_count
            run.context_truncated = context.truncated

        self._session.query(GovernanceEvent).filter(
            GovernanceEvent.analysis_run_id == run.id
        ).delete()
        for sequence, decision in enumerate(state.get("governance_decisions", []) or []):
            self._session.add(
                GovernanceEvent(
                    analysis_run_id=run.id,
                    sequence=sequence,
                    decision_id=str(decision.get("decision_id", "")),
                    node_name=str(decision.get("node_name", "")),
                    construct_name=str(decision.get("construct_name", "")),
                    construct_type=str(decision.get("construct_type", "")),
                    outcome=str(decision.get("outcome", "")),
                    source_count=int(decision.get("source_count", 0)),
                    confidence=decision.get("confidence"),
                    terminal_state_name=decision.get("terminal_state_name"),
                    recorded_at=str(decision.get("recorded_at", "")),
                )
            )

        completed = state.get("completed_at")
        run.completed_at = (
            completed if isinstance(completed, datetime) else datetime.now(timezone.utc)
        )

    def _ledger_length(self) -> int:
        try:
            return sum(1 for _ in get_verba_ledger().store.all_entries())
        except Exception:
            logger.exception("Unable to read the governance ledger length")
            return 0

    def _persist_ledger_entries(self, run: AnalysisRun, start: int) -> None:
        """Project this run's slice of the hash chain into the database."""
        try:
            entries = list(get_verba_ledger().store.all_entries())[start:]
        except Exception:
            logger.exception("Unable to read governance ledger entries")
            return

        identity = run.governance_instance_id
        self._session.query(LedgerEntryRecord).filter(
            LedgerEntryRecord.analysis_run_id == run.id
        ).delete()
        for entry in entries:
            if identity and entry.identity_key != identity:
                continue
            self._session.add(
                LedgerEntryRecord(
                    analysis_run_id=run.id,
                    entry_id=entry.entry_id,
                    sequence=entry.sequence,
                    entry_type=entry.entry_type.value,
                    identity_key=entry.identity_key,
                    instance_id=entry.instance_id,
                    decision_id=entry.decision_id,
                    caused_by=entry.caused_by,
                    payload=dict(entry.payload),
                    timestamp=entry.timestamp,
                    prev_hash=entry.prev_hash,
                    entry_hash=entry.entry_hash,
                )
            )


def _enum_value(value: Any, default: str) -> str:
    if value is None:
        return default
    return str(getattr(value, "value", value))


def _text(value: Any) -> str | None:
    return None if value is None else str(value)
