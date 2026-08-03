from enum import Enum


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    GOVERNANCE_BLOCKED = "governance_blocked"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class WorkflowStage(str, Enum):
    VALIDATION = "validation"
    RETRIEVAL = "retrieval"
    PROCESS_DISCOVERY = "process_discovery"
    BOTTLENECK_ANALYSIS = "bottleneck_analysis"
    RISK_ANALYSIS = "risk_analysis"
    AUTOMATION_ANALYSIS = "automation_analysis"
    FINAL_SYNTHESIS = "final_synthesis"
    COMPLETED = "completed"
    FAILED = "failed"
    GOVERNANCE_BLOCKED = "governance_blocked"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
