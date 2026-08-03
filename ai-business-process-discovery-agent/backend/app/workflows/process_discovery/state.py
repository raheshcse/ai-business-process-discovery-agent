from datetime import datetime
from typing import Any, TypedDict

from vsl_core.exceptions import AutomationDeniedException

from app.governance.process_discovery.models import (
    GovernanceDecisionData,
    GovernanceDenialData,
    GovernanceStage,
    GovernanceStatus,
)
from app.llm.models import BusinessAnalysisResult
from app.rag.service import RAGResult
from app.workflows.process_discovery.models import WorkflowStage, WorkflowStatus


class ProcessDiscoveryState(TypedDict, total=False):
    workflow_id: str
    project_id: str
    question: str
    document_id_filters: list[str]
    metadata_filters: dict[str, Any]
    top_k: int
    minimum_similarity_score: float | None
    rag_result: RAGResult | None
    process_analysis: BusinessAnalysisResult | None
    bottleneck_analysis: BusinessAnalysisResult | None
    risk_analysis: BusinessAnalysisResult | None
    automation_analysis: BusinessAnalysisResult | None
    final_analysis: BusinessAnalysisResult | None
    current_stage: WorkflowStage
    status: WorkflowStatus
    errors: list[str]
    started_at: datetime
    completed_at: datetime | None
    governance_status: GovernanceStatus
    governance_stage: GovernanceStage
    vsl_denial: AutomationDeniedException | None
    denial_summary: GovernanceDenialData | None
    terminal_state_name: str | None
    governance_decisions: list[GovernanceDecisionData]
    human_review_required: bool
    governance_instance_id: str
