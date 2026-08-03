from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GovernanceStatus(str, Enum):
    PENDING = "pending"
    MONITORING = "monitoring"
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class GovernanceStage(str, Enum):
    VALIDATION = "validation"
    PROCESS_DISCOVERY = "process_discovery"
    PROCESS_INVARIANT = "process_invariant"
    BOTTLENECK_ANALYSIS = "bottleneck_analysis"
    BOTTLENECK_INVARIANT = "bottleneck_invariant"
    RISK_ANALYSIS = "risk_analysis"
    RISK_INVARIANT = "risk_invariant"
    AUTOMATION_ANALYSIS = "automation_analysis"
    AUTOMATION_INVARIANT = "automation_invariant"
    FINAL_SYNTHESIS = "final_synthesis"
    FINAL_INVARIANT = "final_invariant"
    TERMINAL = "terminal"


class GovernanceDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision_id: str
    node_name: str
    construct_name: str
    construct_type: str
    outcome: str
    source_count: int = Field(ge=0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    terminal_state_name: str | None = None
    recorded_at: str


class GovernanceDenialSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    construct_name: str
    denial_type: str
    safe_reason: str
    terminal_state_name: str
    human_review_required: bool


GovernanceDecisionData = dict[str, Any]
GovernanceDenialData = dict[str, Any]
