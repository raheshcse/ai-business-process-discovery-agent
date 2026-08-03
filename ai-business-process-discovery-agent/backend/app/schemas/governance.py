from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class GovernanceEventResponse(BaseModel):
    """One PreNode, invariant or terminal-state decision."""

    sequence: int
    decision_id: str
    node_name: str
    construct_name: str
    construct_type: str
    outcome: str
    source_count: int
    confidence: float | None
    terminal_state_name: str | None
    recorded_at: str

    model_config = ConfigDict(from_attributes=True)


class LedgerEntryResponse(BaseModel):
    """One entry in the hash-chained VerbaLedger."""

    entry_id: str
    sequence: int
    entry_type: str
    identity_key: str
    instance_id: str | None
    decision_id: str | None
    caused_by: str | None
    payload: dict[str, Any]
    timestamp: float
    prev_hash: str
    entry_hash: str

    model_config = ConfigDict(from_attributes=True)


class LedgerAuditCheck(BaseModel):
    """One of the five VerbaLedger audit checks, in business language.

    `passed` is reported exactly as the ledger reports it. Two checks are
    expected to fail in this application because it has no human-approval
    or specification-update workflow yet; `explanation` says so rather than
    presenting a failure as a pass.
    """

    name: str
    label: str
    passed: bool
    explanation: str
    violation_count: int


class GovernanceReport(BaseModel):
    """Everything the Governance & Audit screen needs for one run."""

    analysis_run_id: str
    project_id: str
    question: str

    workflow_status: str
    governance_status: str
    governance_stage: str
    terminal_state_name: str | None
    human_review_required: bool
    denial_summary: dict[str, Any] | None
    errors: list[str]

    decisions: list[GovernanceEventResponse]
    ledger_entries: list[LedgerEntryResponse]

    chain_verified: bool
    checkpoint_sequence: int | None
    checkpoint_hash: str | None
    audit_checks: list[LedgerAuditCheck]
    certificate_issued: bool
    certificate_hash: str | None
    certificate_note: str | None


class GovernanceConstruct(BaseModel):
    """Static description of a gate the workflow applies to every run."""

    name: str
    kind: str
    stage: str
    description: str
    on_violation: str | None


class GovernanceCatalogue(BaseModel):
    """The governance rulebook, so the UI can explain gates that never
    fired as well as gates that did."""

    gamma_threshold: float
    minimum_evidence_score: float
    minimum_process_findings: int
    pre_nodes: list[GovernanceConstruct]
    invariants: list[GovernanceConstruct]
    terminal_states: list[GovernanceConstruct]
