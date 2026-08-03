"""Governance and audit read endpoints.

Everything here is derived from what the workflow actually recorded. The
audit checks are reported exactly as `VerbaLedger.audit()` returns them --
including the two this application is expected to fail, because it has no
human-approval or specification-update workflow. Presenting those as
passing would be the one thing an audit screen must never do.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from vsl_core.ledger import VerbaCertificate

from app.core.composition import get_governance_gates, get_verba_ledger
from app.core.config import settings
from app.core.database import get_db
from app.governance.process_discovery.policies import (
    GOVERNANCE_BLOCKED,
    HUMAN_REVIEW_REQUIRED,
    INSUFFICIENT_EVIDENCE,
    UNSUPPORTED_FINDINGS,
)
from app.schemas.governance import (
    GovernanceCatalogue,
    GovernanceConstruct,
    GovernanceEventResponse,
    GovernanceReport,
    LedgerAuditCheck,
    LedgerEntryResponse,
)
from app.services.analysis_run_service import (
    AnalysisRunNotFoundError,
    AnalysisRunService,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Governance"])

DbSession = Annotated[Session, Depends(get_db)]

# Plain-language wording for the five Section 10 ledger checks. The two
# marked as structurally unmet are honest statements about this
# application's scope, not excuses generated at runtime.
_CHECK_COPY: dict[str, tuple[str, str, str]] = {
    "no_monitoring_gaps": (
        "Continuous monitoring",
        "Every governance checkpoint ran within the configured time window, "
        "so no stretch of the workflow went unmonitored.",
        "Monitoring checkpoints were further apart than the configured limit.",
    ),
    "drift_flagged_monitor_has_pre_node": (
        "Flagged concerns were acted on",
        "Every time a readiness check flagged a concern, a governance gate "
        "was recorded in response.",
        "A readiness check flagged a concern with no governance gate recorded "
        "in response.",
    ),
    "pre_node_has_verification": (
        "Gate decisions were verified",
        "Every governance gate that ran has a matching verification record.",
        "A governance gate ran without a matching verification record.",
    ),
    "insufficient_verification_has_specification_update": (
        "Failures triggered a rule update",
        "Every failed verification was followed by an update to the "
        "governance rules.",
        "This application has no rule-update workflow, so a failed "
        "verification is recorded and the run stops rather than the rules "
        "being revised. Expected to fail until an approval workflow exists.",
    ),
    "terminal_has_human_authorised_transition": (
        "Stopped runs were human-authorised",
        "Every run that stopped at a terminal state was signed off by an "
        "authorised person.",
        "This application has no human approval or re-enablement workflow, so "
        "a stopped run has no recorded human sign-off. Expected to fail until "
        "an approval workflow exists.",
    ),
}


@router.get("/analyses/{run_id}/governance", response_model=GovernanceReport)
def get_governance_report(run_id: str, db: DbSession) -> GovernanceReport:
    try:
        run = AnalysisRunService(db).get_run(run_id)
    except AnalysisRunNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis not found") from exc

    ledger = get_verba_ledger()
    try:
        chain_verified = ledger.verify_integrity()
        report = ledger.audit(
            max_monitor_gap_seconds=settings.governance_max_monitor_gap_seconds
        )
        checkpoint = ledger.current_checkpoint()
        certificate = ledger.issue_certificate(
            max_monitor_gap_seconds=settings.governance_max_monitor_gap_seconds
        )
    except Exception:
        # A ledger that cannot be read is itself a governance finding, so
        # the screen still renders with the failure made explicit.
        logger.exception("Governance ledger could not be inspected")
        chain_verified = False
        report = None
        checkpoint = None
        certificate = None

    audit_checks: list[LedgerAuditCheck] = []
    if report is not None:
        for name in (*report.checks_passed, *report.checks_failed):
            passed = name in report.checks_passed
            label, passed_copy, failed_copy = _CHECK_COPY.get(
                name, (name, "Check passed.", "Check failed.")
            )
            audit_checks.append(
                LedgerAuditCheck(
                    name=name,
                    label=label,
                    passed=passed,
                    explanation=passed_copy if passed else failed_copy,
                    violation_count=len(report.violations.get(name, [])),
                )
            )

    return GovernanceReport(
        analysis_run_id=run.id,
        project_id=run.project_id,
        question=run.question,
        workflow_status=run.status,
        governance_status=run.governance_status,
        governance_stage=run.governance_stage,
        terminal_state_name=run.terminal_state_name,
        human_review_required=run.human_review_required,
        denial_summary=run.denial_summary,
        errors=list(run.errors or []),
        decisions=[
            GovernanceEventResponse.model_validate(event)
            for event in run.governance_events
        ],
        ledger_entries=[
            LedgerEntryResponse.model_validate(entry) for entry in run.ledger_entries
        ],
        chain_verified=chain_verified,
        checkpoint_sequence=checkpoint.sequence if checkpoint else None,
        checkpoint_hash=checkpoint.entry_hash if checkpoint else None,
        audit_checks=audit_checks,
        certificate_issued=certificate is not None,
        certificate_hash=certificate.certificate_hash if certificate else None,
        certificate_note=VerbaCertificate.NOTE,
    )


@router.get("/governance/catalogue", response_model=GovernanceCatalogue)
def get_governance_catalogue() -> GovernanceCatalogue:
    """The rulebook applied to every run, read off the compiled gates."""
    invariants = get_governance_gates().invariants
    return GovernanceCatalogue(
        gamma_threshold=settings.governance_gamma_threshold,
        minimum_evidence_score=settings.governance_minimum_evidence_score,
        minimum_process_findings=settings.governance_minimum_process_findings,
        pre_nodes=[
            GovernanceConstruct(
                name="process_discovery_pre_node",
                kind="pre_node",
                stage="process_discovery",
                description=(
                    "Checks there is scoped, usable evidence from this "
                    "project's documents before any process analysis runs."
                ),
                on_violation=GOVERNANCE_BLOCKED.name,
            ),
            GovernanceConstruct(
                name="bottleneck_analysis_pre_node",
                kind="pre_node",
                stage="bottleneck_analysis",
                description=(
                    "Checks the process analysis produced evidence-backed "
                    "findings before bottlenecks are analysed."
                ),
                on_violation=GOVERNANCE_BLOCKED.name,
            ),
            GovernanceConstruct(
                name="risk_analysis_pre_node",
                kind="pre_node",
                stage="risk_analysis",
                description=(
                    "Checks admissible evidence exists before operational "
                    "risk analysis runs."
                ),
                on_violation=GOVERNANCE_BLOCKED.name,
            ),
            GovernanceConstruct(
                name="automation_analysis_pre_node",
                kind="pre_node",
                stage="automation_analysis",
                description=(
                    "Checks both process and bottleneck evidence exist "
                    "before automation opportunities are proposed."
                ),
                on_violation=HUMAN_REVIEW_REQUIRED.name,
            ),
            GovernanceConstruct(
                name="final_synthesis_pre_node",
                kind="pre_node",
                stage="final_synthesis",
                description=(
                    "Checks every earlier analysis passed its invariants "
                    "before the executive summary is written."
                ),
                on_violation=GOVERNANCE_BLOCKED.name,
            ),
        ],
        invariants=[
            GovernanceConstruct(
                name=invariant.name,
                kind="invariant",
                stage=stage,
                description=invariant.description,
                on_violation=(
                    invariant.on_violation.name
                    if invariant.on_violation is not None
                    else None
                ),
            )
            for invariant, stage in (
                (invariants.evidence_reference, "process_invariant"),
                (invariants.process_analysis, "process_invariant"),
                (invariants.bottleneck_analysis, "bottleneck_invariant"),
                (invariants.risk_scope, "risk_invariant"),
                (invariants.automation_safety, "automation_invariant"),
                (invariants.final_analysis, "final_invariant"),
            )
        ],
        terminal_states=[
            GovernanceConstruct(
                name=state.name,
                kind="terminal_state",
                stage="terminal",
                description=state.description,
                on_violation=None,
            )
            for state in (
                GOVERNANCE_BLOCKED,
                INSUFFICIENT_EVIDENCE,
                UNSUPPORTED_FINDINGS,
                HUMAN_REVIEW_REQUIRED,
            )
        ],
    )
