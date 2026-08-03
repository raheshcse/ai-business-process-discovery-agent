from dataclasses import dataclass
from typing import Any, Mapping

from vsl_core.constructs import Invariant
from vsl_core.metrics import AssuranceBasis, F2Modification

from app.governance.process_discovery.monitors import _available_source_ids
from app.governance.process_discovery.policies import (
    HUMAN_REVIEW_REQUIRED,
    UNSUPPORTED_FINDINGS,
)

# Output checks occur after model generation and do not alter the model's
# formation process, so neither F1 nor F2 is claimed.
OUTPUT_VALIDATION_ASSURANCE = AssuranceBasis(
    f1_pre_commitment=False,
    f2_modification=F2Modification.NONE,
)

_LEGAL_CONCLUSION_PHRASES = (
    "is legally compliant",
    "is regulatory compliant",
    "violates the law",
    "is illegal",
    "guarantees compliance",
)
_HUMAN_REVIEW_PHRASES = (
    "human review",
    "human approval",
    "human oversight",
    "manual approval",
)
_AUTONOMOUS_PHRASES = (
    "fully automate",
    "autonomous execution",
    "without human",
    "no human review",
)


@dataclass(frozen=True)
class ProcessDiscoveryInvariants:
    evidence_reference: Invariant
    process_analysis: Invariant
    bottleneck_analysis: Invariant
    risk_scope: Invariant
    automation_safety: Invariant
    final_analysis: Invariant


def build_process_discovery_invariants() -> ProcessDiscoveryInvariants:
    return ProcessDiscoveryInvariants(
        evidence_reference=Invariant(
            name="evidence_reference_invariant",
            description="Every process finding must cite available RAG sources.",
            rule=_process_evidence_references_hold,
            assurance_basis=OUTPUT_VALIDATION_ASSURANCE,
            on_violation=UNSUPPORTED_FINDINGS,
        ),
        process_analysis=Invariant(
            name="process_analysis_invariant",
            description="Process findings must be evidence-grounded process claims.",
            rule=_process_analysis_holds,
            assurance_basis=OUTPUT_VALIDATION_ASSURANCE,
            on_violation=UNSUPPORTED_FINDINGS,
        ),
        bottleneck_analysis=Invariant(
            name="bottleneck_analysis_invariant",
            description="Bottleneck findings must be supported by available sources.",
            rule=_bottleneck_claims_hold,
            assurance_basis=OUTPUT_VALIDATION_ASSURANCE,
            on_violation=UNSUPPORTED_FINDINGS,
        ),
        risk_scope=Invariant(
            name="risk_scope_invariant",
            description="Risk findings stay operational and avoid legal conclusions.",
            rule=_risk_scope_holds,
            assurance_basis=OUTPUT_VALIDATION_ASSURANCE,
            on_violation=UNSUPPORTED_FINDINGS,
        ),
        automation_safety=Invariant(
            name="automation_safety_invariant",
            description="High-risk automation retains appropriate human review.",
            rule=_automation_safety_holds,
            assurance_basis=OUTPUT_VALIDATION_ASSURANCE,
            on_violation=HUMAN_REVIEW_REQUIRED,
        ),
        final_analysis=Invariant(
            name="final_analysis_invariant",
            description="Final synthesis stays grounded and exposes uncertainty.",
            rule=_final_analysis_holds,
            assurance_basis=OUTPUT_VALIDATION_ASSURANCE,
            on_violation=UNSUPPORTED_FINDINGS,
        ),
    )


async def _process_evidence_references_hold(
    state: Mapping[str, Any],
) -> bool:
    return _analysis_is_grounded(state.get("process_analysis"), state)


async def _process_analysis_holds(state: Mapping[str, Any]) -> bool:
    analysis = state.get("process_analysis")
    if not _analysis_is_grounded(analysis, state):
        return False
    return all(
        getattr(finding.category, "value", finding.category)
        in {"process", "role", "control", "data", "technology", "other"}
        for finding in analysis.findings
    )


async def _bottleneck_claims_hold(state: Mapping[str, Any]) -> bool:
    analysis = state.get("bottleneck_analysis")
    if not _analysis_is_grounded(analysis, state):
        return False
    return all(
        getattr(finding.category, "value", finding.category)
        in {"bottleneck", "process", "control", "technology", "other"}
        for finding in analysis.findings
    )


async def _risk_scope_holds(state: Mapping[str, Any]) -> bool:
    analysis = state.get("risk_analysis")
    if not _analysis_is_grounded(analysis, state):
        return False
    content = " ".join(
        [
            analysis.summary,
            *(
                f"{finding.title} {finding.description} {finding.recommendation}"
                for finding in analysis.findings
            ),
        ]
    ).lower()
    categories_valid = all(
        getattr(finding.category, "value", finding.category)
        in {"risk", "control", "data", "technology", "role", "other"}
        for finding in analysis.findings
    )
    return categories_valid and not any(
        phrase in content for phrase in _LEGAL_CONCLUSION_PHRASES
    )


async def _automation_safety_holds(state: Mapping[str, Any]) -> bool:
    analysis = state.get("automation_analysis")
    if not _analysis_is_grounded(analysis, state):
        return False
    for finding in analysis.findings:
        content = (
            f"{finding.title} {finding.description} {finding.recommendation}"
        ).lower()
        severity = getattr(finding.severity, "value", finding.severity)
        requires_review = severity in {"high", "critical"} or any(
            phrase in content for phrase in _AUTONOMOUS_PHRASES
        )
        explicitly_removes_review = (
            "without human" in content or "no human review" in content
        )
        if requires_review and (
            explicitly_removes_review
            or not any(phrase in content for phrase in _HUMAN_REVIEW_PHRASES)
        ):
            return False
        if "human-dependent" in content and "human" not in finding.recommendation.lower():
            return False
    return True


async def _final_analysis_holds(state: Mapping[str, Any]) -> bool:
    analysis = state.get("final_analysis")
    if not _analysis_is_grounded(analysis, state):
        return False
    if not isinstance(analysis.assumptions, list):
        return False
    if not isinstance(analysis.insufficient_evidence, list):
        return False
    return not any(
        decision.get("outcome") == "denied"
        for decision in state.get("governance_decisions", [])
    )


def _analysis_is_grounded(
    analysis: Any, state: Mapping[str, Any]
) -> bool:
    if analysis is None:
        return False
    available = _available_source_ids(state)
    findings = list(getattr(analysis, "findings", []) or [])
    if not findings:
        return bool(
            getattr(analysis, "insufficient_evidence", [])
            or getattr(analysis, "assumptions", [])
        )
    for finding in findings:
        source_ids = set(finding.evidence_source_ids)
        if not source_ids or not source_ids.issubset(available):
            return False
    return True
