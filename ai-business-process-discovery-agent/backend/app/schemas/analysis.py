from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.llm.models import BusinessAnalysisResult
from app.workflows.process_discovery import WorkflowStage, WorkflowStatus


class AnalysisRunCreate(BaseModel):
    """Request to start a governed process-discovery run."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=5, max_length=2_000)
    top_k: int | None = Field(default=None, ge=1, le=50)
    minimum_similarity_score: float | None = Field(default=None, ge=-1.0, le=1.0)
    document_id_filters: list[str] = Field(default_factory=list)

    @field_validator("question")
    @classmethod
    def _question_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be blank")
        return value.strip()

    @field_validator("document_id_filters")
    @classmethod
    def _unique_non_empty(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("document_id_filters must be unique")
        return cleaned


class CitationResponse(BaseModel):
    """One retrieved evidence chunk, keyed by the `Source N` marker the
    model was shown, so findings can be traced back to a document."""

    source_id: str
    document_id: str
    chunk_id: str
    chunk_index: int
    score: float
    filename: str | None = None


class AnalysisRunSummary(BaseModel):
    """List-view projection: enough for a table row, no heavy payloads."""

    id: str
    project_id: str
    question: str
    status: WorkflowStatus
    current_stage: WorkflowStage
    governance_status: str
    terminal_state_name: str | None
    human_review_required: bool
    source_count: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AnalysisRunDetail(AnalysisRunSummary):
    """Everything the results screen renders."""

    top_k: int
    minimum_similarity_score: float | None
    document_id_filters: list[str]
    governance_stage: str
    errors: list[str]
    denial_summary: dict[str, Any] | None

    process_analysis: BusinessAnalysisResult | None
    bottleneck_analysis: BusinessAnalysisResult | None
    risk_analysis: BusinessAnalysisResult | None
    automation_analysis: BusinessAnalysisResult | None
    final_analysis: BusinessAnalysisResult | None

    citations: list[CitationResponse]
    retrieval_provider: str | None
    retrieval_model: str | None
    retrieved_count: int
    context_truncated: bool

    model_config = ConfigDict(from_attributes=True)
