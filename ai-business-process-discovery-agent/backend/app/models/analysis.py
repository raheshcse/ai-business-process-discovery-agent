"""Persistence for governed process-discovery runs.

The LangGraph workflow already produces everything the UI needs, but it
produces it in volatile `ProcessDiscoveryState`. These tables give a run an
identity that survives the request, so the frontend can start a run, poll
it, and re-open its results and audit trail later.

Nothing here changes how the workflow itself behaves.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AnalysisRun(Base):
    """One invocation of the governed process-discovery graph."""

    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # --- Request ------------------------------------------------------
    question: Mapped[str] = mapped_column(Text, nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    minimum_similarity_score: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    document_id_filters: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )
    metadata_filters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # --- Workflow outcome --------------------------------------------
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    current_stage: Mapped[str] = mapped_column(
        String(40), nullable=False, default="validation"
    )
    errors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # --- Governance outcome ------------------------------------------
    governance_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="pending"
    )
    governance_stage: Mapped[str] = mapped_column(
        String(40), nullable=False, default="validation"
    )
    terminal_state_name: Mapped[str | None] = mapped_column(String(60), nullable=True)
    human_review_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    denial_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    workflow_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    governance_instance_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )

    # --- Analyses (serialised BusinessAnalysisResult) ------------------
    process_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    bottleneck_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    risk_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    automation_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    final_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # --- Evidence -----------------------------------------------------
    citations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    retrieval_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    retrieval_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    retrieved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    context_truncated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    governance_events: Mapped[list["GovernanceEvent"]] = relationship(
        back_populates="analysis_run",
        cascade="all, delete-orphan",
        order_by="GovernanceEvent.sequence",
    )
    ledger_entries: Mapped[list["LedgerEntryRecord"]] = relationship(
        back_populates="analysis_run",
        cascade="all, delete-orphan",
        order_by="LedgerEntryRecord.sequence",
    )


class GovernanceEvent(Base):
    """A single allow/deny decision recorded by the governance ledger.

    Mirrors `GovernanceDecision` from
    `app.governance.process_discovery.models` one-for-one so the API can
    hand the frontend exactly what the workflow produced.
    """

    __tablename__ = "governance_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    analysis_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    decision_id: Mapped[str] = mapped_column(String(36), nullable=False)
    node_name: Mapped[str] = mapped_column(String(120), nullable=False)
    construct_name: Mapped[str] = mapped_column(String(120), nullable=False)
    construct_type: Mapped[str] = mapped_column(String(40), nullable=False)
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    terminal_state_name: Mapped[str | None] = mapped_column(String(60), nullable=True)
    recorded_at: Mapped[str] = mapped_column(String(40), nullable=False)

    analysis_run: Mapped["AnalysisRun"] = relationship(
        back_populates="governance_events"
    )


class LedgerEntryRecord(Base):
    """A snapshot of one hash-chained VerbaLedger entry for this run.

    The authoritative chain lives in the append-only JSONL ledger store.
    This is a queryable projection so the audit screen does not have to
    scan the whole file, and so integrity can be re-checked by comparing
    the two.
    """

    __tablename__ = "ledger_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    analysis_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    entry_id: Mapped[str] = mapped_column(String(36), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_type: Mapped[str] = mapped_column(String(40), nullable=False)
    identity_key: Mapped[str] = mapped_column(String(128), nullable=False)
    instance_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    caused_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    analysis_run: Mapped["AnalysisRun"] = relationship(back_populates="ledger_entries")
