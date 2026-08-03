import uuid
from datetime import datetime, timezone
from typing import Any, Mapping

from vsl_core.exceptions import AutomationDeniedException, InvariantViolation
from vsl_core.ledger import (
    LedgerEntryType,
    VerbaLedger,
    VerificationResult,
)

from app.governance.process_discovery.models import (
    GovernanceDecision,
    GovernanceDenialSummary,
)
from app.governance.process_discovery.policies import (
    GOVERNANCE_BLOCKED,
    HUMAN_REVIEW_REQUIRED,
    INSUFFICIENT_EVIDENCE,
)

_PRE_NODE_TERMINALS = {
    "automation_analysis_pre_node": HUMAN_REVIEW_REQUIRED.name,
}


class ProcessDiscoveryGovernanceLedger:
    """Safe application-level recording over an injected VerbaLedger."""

    def __init__(self, ledger: VerbaLedger) -> None:
        self._ledger = ledger

    @property
    def ledger(self) -> VerbaLedger:
        return self._ledger

    def record_allowed(
        self,
        state: Mapping[str, Any],
        *,
        node_name: str,
        construct_name: str,
        construct_type: str,
        confidence: float | None = None,
    ) -> dict[str, Any]:
        decision_id = str(uuid.uuid4())
        common = self._common(state, decision_id)
        payload = self._safe_payload(
            state,
            node_name=node_name,
            outcome="allowed",
            confidence=confidence,
        )
        caused_by: str | None = None
        if construct_type == "pre_node":
            monitor = self._ledger.write_monitor(
                **common,
                drift_detected=False,
                extra_payload=payload,
            )
            pre_node = self._ledger.write(
                LedgerEntryType.PRE_NODE,
                **common,
                caused_by=monitor.entry_id,
                payload=payload,
            )
            caused_by = pre_node.entry_id
        self._ledger.write_verification(
            **common,
            caused_by=caused_by,
            result=VerificationResult.SUFFICIENT,
            extra_payload=payload,
        )
        return GovernanceDecision(
            decision_id=decision_id,
            node_name=node_name,
            construct_name=construct_name,
            construct_type=construct_type,
            outcome="allowed",
            source_count=payload["source_count"],
            confidence=confidence,
            recorded_at=datetime.now(timezone.utc).isoformat(),
        ).model_dump(mode="json")

    def record_denial(
        self,
        state: Mapping[str, Any],
        denial: AutomationDeniedException,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        construct_name = _construct_name(denial)
        construct_type = (
            "invariant" if isinstance(denial, InvariantViolation) else "pre_node"
        )
        terminal_state_name = _terminal_state_name(denial, construct_name)
        human_review = terminal_state_name == HUMAN_REVIEW_REQUIRED.name
        decision_id = str(uuid.uuid4())
        common = self._common(state, decision_id)
        payload = self._safe_payload(
            state,
            node_name=construct_name,
            outcome="denied",
            terminal_state_name=terminal_state_name,
        )
        caused_by: str | None = None
        if construct_type == "pre_node":
            monitor = self._ledger.write_monitor(
                **common,
                drift_detected=True,
                extra_payload=payload,
            )
            pre_node = self._ledger.write(
                LedgerEntryType.PRE_NODE,
                **common,
                caused_by=monitor.entry_id,
                payload=payload,
            )
            caused_by = pre_node.entry_id
        verification = self._ledger.write_verification(
            **common,
            caused_by=caused_by,
            result=VerificationResult.INSUFFICIENT,
            extra_payload=payload,
        )
        self._ledger.write(
            LedgerEntryType.TERMINAL,
            **common,
            caused_by=verification.entry_id,
            payload=payload,
        )
        decision = GovernanceDecision(
            decision_id=decision_id,
            node_name=construct_name,
            construct_name=construct_name,
            construct_type=construct_type,
            outcome="denied",
            source_count=payload["source_count"],
            terminal_state_name=terminal_state_name,
            recorded_at=datetime.now(timezone.utc).isoformat(),
        ).model_dump(mode="json")
        summary = GovernanceDenialSummary(
            construct_name=construct_name,
            denial_type=type(denial).__name__,
            safe_reason=f"Governance denied automated execution at {construct_name}.",
            terminal_state_name=terminal_state_name,
            human_review_required=human_review,
        ).model_dump(mode="json")
        return decision, summary

    def record_insufficient_evidence(
        self, state: Mapping[str, Any]
    ) -> dict[str, Any]:
        decision_id = str(uuid.uuid4())
        common = self._common(state, decision_id)
        payload = self._safe_payload(
            state,
            node_name="retrieve_evidence",
            outcome="insufficient_evidence",
            terminal_state_name=INSUFFICIENT_EVIDENCE.name,
        )
        self._ledger.write(
            LedgerEntryType.TERMINAL,
            **common,
            payload=payload,
        )
        return GovernanceDecision(
            decision_id=decision_id,
            node_name="retrieve_evidence",
            construct_name=INSUFFICIENT_EVIDENCE.name,
            construct_type="terminal_state",
            outcome="insufficient_evidence",
            source_count=payload["source_count"],
            terminal_state_name=INSUFFICIENT_EVIDENCE.name,
            recorded_at=datetime.now(timezone.utc).isoformat(),
        ).model_dump(mode="json")

    @staticmethod
    def _common(
        state: Mapping[str, Any], decision_id: str
    ) -> dict[str, Any]:
        return {
            "identity_key": str(
                state.get("governance_instance_id")
                or state.get("workflow_id")
                or "process-discovery"
            ),
            "instance_id": str(state.get("workflow_id") or ""),
            "decision_id": decision_id,
        }

    @staticmethod
    def _safe_payload(
        state: Mapping[str, Any],
        *,
        node_name: str,
        outcome: str,
        confidence: float | None = None,
        terminal_state_name: str | None = None,
    ) -> dict[str, Any]:
        rag_result = state.get("rag_result")
        context = getattr(rag_result, "context", None)
        payload: dict[str, Any] = {
            "node_name": node_name,
            "outcome": outcome,
            "source_count": int(getattr(context, "source_count", 0)),
        }
        if confidence is not None:
            payload["confidence"] = confidence
        if terminal_state_name is not None:
            payload["terminal_state_name"] = terminal_state_name
        return payload


# Backward-compatible public name retained for callers that adopted the
# original governance-ledger API. Both names refer to the same injected
# VerbaLedger wrapper and therefore share no implicit or global state.
ProcessDiscoveryLedger = ProcessDiscoveryGovernanceLedger


def _construct_name(denial: AutomationDeniedException) -> str:
    if isinstance(denial, InvariantViolation) and denial.invariant_name:
        return denial.invariant_name
    reason = denial.reason
    for quote in ("'", '"'):
        parts = reason.split(quote)
        if len(parts) >= 3 and parts[1]:
            return parts[1]
    return "unknown_governance_gate"


def _terminal_state_name(
    denial: AutomationDeniedException, construct_name: str
) -> str:
    if isinstance(denial, InvariantViolation) and denial.terminal_state_name:
        return denial.terminal_state_name
    return _PRE_NODE_TERMINALS.get(
        construct_name,
        GOVERNANCE_BLOCKED.name,
    )
