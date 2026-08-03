import asyncio
import json
from typing import Any

import pytest
from vsl_core.ledger import LedgerEntryType, VerbaLedger

from app.governance.process_discovery import build_process_discovery_governance
from app.governance.process_discovery.ledger import (
    ProcessDiscoveryGovernanceLedger,
)
from app.workflows.process_discovery import (
    WorkflowStatus,
    build_process_discovery_graph,
)
from tests.governance.test_vsl_integration import gates_with_denial
from tests.workflows.helpers import (
    FakeAnalysisService,
    FakeRAGService,
    analysis_result,
    rag_result,
    workflow_input,
)


def invoke(
    *,
    rag: FakeRAGService | None = None,
    analysis: FakeAnalysisService | None = None,
    gates: Any = None,
    ledger: VerbaLedger | None = None,
    input_value: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], FakeRAGService, FakeAnalysisService, VerbaLedger]:
    resolved_rag = rag or FakeRAGService()
    resolved_analysis = analysis or FakeAnalysisService()
    resolved_ledger = ledger or VerbaLedger()
    graph = build_process_discovery_graph(
        resolved_rag,  # type: ignore[arg-type]
        resolved_analysis,  # type: ignore[arg-type]
        gates or build_process_discovery_governance(),
        ProcessDiscoveryGovernanceLedger(resolved_ledger),
    )
    result = asyncio.run(graph.ainvoke(input_value or workflow_input()))
    return result, resolved_rag, resolved_analysis, resolved_ledger


def test_successful_governed_workflow_records_all_decisions() -> None:
    result, _, analysis, ledger = invoke()
    assert result["status"] == WorkflowStatus.COMPLETED
    assert len(analysis.calls) == 5
    assert len(result["governance_decisions"]) == 11
    assert all(
        decision["outcome"] == "allowed"
        for decision in result["governance_decisions"]
    )
    assert ledger.verify_integrity()


@pytest.mark.parametrize(
    ("field", "construct_name", "expected_analysis_calls"),
    [
        ("process_discovery", "process_discovery_pre_node", 0),
        ("bottleneck_analysis", "bottleneck_analysis_pre_node", 1),
        ("risk_analysis", "risk_analysis_pre_node", 2),
        ("automation_analysis", "automation_analysis_pre_node", 3),
        ("final_synthesis", "final_synthesis_pre_node", 4),
    ],
)
def test_each_pre_node_denies_before_protected_analysis(
    field: str,
    construct_name: str,
    expected_analysis_calls: int,
) -> None:
    result, _, analysis, _ = invoke(
        gates=gates_with_denial(field, construct_name)
    )
    assert len(analysis.calls) == expected_analysis_calls
    assert result["status"] in {
        WorkflowStatus.GOVERNANCE_BLOCKED,
        WorkflowStatus.HUMAN_REVIEW_REQUIRED,
    }
    assert result["denial_summary"]["construct_name"] == construct_name
    assert result["completed_at"] is not None


def test_out_of_scope_evidence_denies_process_discovery() -> None:
    evidence = rag_result()
    evidence.context.citations[0].metadata["project_id"] = "another-project"
    result, _, analysis, _ = invoke(rag=FakeRAGService(result=evidence))
    assert analysis.calls == []
    assert result["status"] == WorkflowStatus.GOVERNANCE_BLOCKED
    assert result["terminal_state_name"] == "GOVERNANCE_BLOCKED"


def test_low_quality_evidence_denies_before_process_discovery() -> None:
    result, _, analysis, _ = invoke(
        rag=FakeRAGService(score=0.4),
        input_value=workflow_input(minimum_similarity_score=None),
    )
    assert analysis.calls == []
    assert result["status"] == WorkflowStatus.GOVERNANCE_BLOCKED


def test_invalid_process_evidence_reference_triggers_invariant_denial() -> None:
    invalid = analysis_result(
        "invalid process", evidence_source_ids=["Source 99"]
    )
    result, _, analysis, _ = invoke(
        analysis=FakeAnalysisService(responses={0: invalid})
    )
    assert len(analysis.calls) == 1
    assert result["status"] == WorkflowStatus.GOVERNANCE_BLOCKED
    assert result["terminal_state_name"] == "UNSUPPORTED_FINDINGS"
    assert result["denial_summary"]["denial_type"] == "InvariantViolation"


def test_unsupported_process_finding_triggers_process_invariant_denial() -> None:
    invalid = analysis_result(
        "unsupported process claim",
        category="opportunity",
        evidence_source_ids=["Source 1"],
    )
    result, _, analysis, _ = invoke(
        analysis=FakeAnalysisService(responses={0: invalid})
    )
    assert len(analysis.calls) == 1
    assert result["status"] == WorkflowStatus.GOVERNANCE_BLOCKED
    assert result["denial_summary"]["construct_name"] == (
        "process_analysis_invariant"
    )


def test_unsupported_bottleneck_triggers_invariant_denial() -> None:
    invalid = analysis_result(
        "unsupported bottleneck",
        category="bottleneck",
        evidence_source_ids=["Source 99"],
    )
    result, _, analysis, _ = invoke(
        analysis=FakeAnalysisService(responses={1: invalid})
    )
    assert len(analysis.calls) == 2
    assert result["terminal_state_name"] == "UNSUPPORTED_FINDINGS"


def test_legal_conclusion_triggers_risk_scope_denial() -> None:
    invalid = analysis_result("risk", category="risk")
    invalid = invalid.model_copy(
        update={"summary": "The organisation violates the law."}
    )
    result, _, analysis, _ = invoke(
        analysis=FakeAnalysisService(responses={2: invalid})
    )
    assert len(analysis.calls) == 3
    assert result["terminal_state_name"] == "UNSUPPORTED_FINDINGS"


def test_unsafe_automation_requires_human_review() -> None:
    invalid = analysis_result(
        "unsafe automation",
        category="opportunity",
        severity="high",
        recommendation="Fully automate execution without human review.",
    )
    result, _, analysis, _ = invoke(
        analysis=FakeAnalysisService(responses={3: invalid})
    )
    assert len(analysis.calls) == 4
    assert result["status"] == WorkflowStatus.HUMAN_REVIEW_REQUIRED
    assert result["terminal_state_name"] == "HUMAN_REVIEW_REQUIRED"
    assert result["human_review_required"] is True


def test_invalid_final_synthesis_triggers_invariant_denial() -> None:
    invalid = analysis_result(
        "invalid final", evidence_source_ids=["Source 99"]
    )
    result, _, analysis, _ = invoke(
        analysis=FakeAnalysisService(responses={4: invalid})
    )
    assert len(analysis.calls) == 5
    assert result["final_analysis"] is invalid
    assert result["terminal_state_name"] == "UNSUPPORTED_FINDINGS"


def test_denial_records_safe_ledger_events_without_sensitive_content() -> None:
    ledger = VerbaLedger()
    result, _, _, ledger = invoke(
        gates=gates_with_denial(
            "process_discovery", "process_discovery_pre_node"
        ),
        ledger=ledger,
        rag=FakeRAGService(
            result=rag_result(text="SENSITIVE DOCUMENT BODY")
        ),
        input_value=workflow_input(
            question="SECRET PROMPT api_key=do-not-record"
        ),
    )
    entries = list(ledger.store.all_entries())
    payload_text = json.dumps([entry.payload for entry in entries])
    assert result["status"] == WorkflowStatus.GOVERNANCE_BLOCKED
    assert {
        LedgerEntryType.MONITOR,
        LedgerEntryType.PRE_NODE,
        LedgerEntryType.VERIFICATION,
        LedgerEntryType.TERMINAL,
    }.issubset({entry.entry_type for entry in entries})
    assert "SECRET PROMPT" not in payload_text
    assert "SENSITIVE DOCUMENT BODY" not in payload_text
    assert "api_key" not in payload_text
    assert "embedding" not in payload_text.lower()


def test_denial_state_has_safe_serialisable_summary() -> None:
    result, _, _, _ = invoke(
        gates=gates_with_denial(
            "process_discovery", "process_discovery_pre_node"
        )
    )
    json.dumps(result["denial_summary"])
    assert "Gamma" not in result["denial_summary"]["safe_reason"]
    assert result["vsl_denial"] is not None


def test_terminal_instance_is_not_automatically_reenabled() -> None:
    rag = FakeRAGService()
    analysis = FakeAnalysisService()
    ledger = VerbaLedger()
    graph = build_process_discovery_graph(
        rag,  # type: ignore[arg-type]
        analysis,  # type: ignore[arg-type]
        gates_with_denial(
            "process_discovery", "process_discovery_pre_node"
        ),
        ProcessDiscoveryGovernanceLedger(ledger),
    )
    first = asyncio.run(graph.ainvoke(workflow_input()))
    call_count = len(analysis.calls)
    second = asyncio.run(graph.ainvoke(first))

    assert first["status"] == WorkflowStatus.GOVERNANCE_BLOCKED
    assert second["status"] == WorkflowStatus.GOVERNANCE_BLOCKED
    assert second["terminal_state_name"] == first["terminal_state_name"]
    assert second["governance_instance_id"] == first["governance_instance_id"]
    assert len(analysis.calls) == call_count
    assert "cannot be automatically restarted" in second["errors"][-1]
