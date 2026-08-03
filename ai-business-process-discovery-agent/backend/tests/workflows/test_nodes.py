from datetime import datetime, timezone

from vsl_core.ledger import VerbaLedger

from app.governance.process_discovery.ledger import (
    ProcessDiscoveryGovernanceLedger,
)
from app.workflows.process_discovery.models import WorkflowStage, WorkflowStatus
from app.workflows.process_discovery.nodes import ProcessDiscoveryNodes
from tests.workflows.helpers import (
    FakeAnalysisService,
    FakeRAGService,
    workflow_input,
)

FIXED_TIME = datetime(2026, 7, 24, 1, 2, 3, tzinfo=timezone.utc)


def nodes(
    rag: FakeRAGService | None = None,
    analysis: FakeAnalysisService | None = None,
) -> ProcessDiscoveryNodes:
    return ProcessDiscoveryNodes(
        rag or FakeRAGService(),  # type: ignore[arg-type]
        analysis or FakeAnalysisService(),  # type: ignore[arg-type]
        ProcessDiscoveryGovernanceLedger(VerbaLedger()),
        clock=lambda: FIXED_TIME,
        id_factory=lambda: "workflow-fixed",
    )


def test_each_node_updates_the_expected_state() -> None:
    workflow_nodes = nodes()
    state = workflow_input()

    state.update(workflow_nodes.validate_input(state))
    assert state["workflow_id"] == "workflow-fixed"
    assert state["status"] == WorkflowStatus.RUNNING
    assert state["current_stage"] == WorkflowStage.VALIDATION
    assert state["started_at"] == FIXED_TIME

    state.update(workflow_nodes.retrieve_evidence(state))
    assert state["rag_result"] is not None
    assert state["current_stage"] == WorkflowStage.RETRIEVAL

    state.update(workflow_nodes.discover_process(state))
    assert state["process_analysis"].summary == "analysis-0 summary"
    assert state["current_stage"] == WorkflowStage.PROCESS_DISCOVERY

    state.update(workflow_nodes.analyse_bottlenecks(state))
    assert state["bottleneck_analysis"].summary == "analysis-1 summary"
    assert state["current_stage"] == WorkflowStage.BOTTLENECK_ANALYSIS

    state.update(workflow_nodes.analyse_risks(state))
    assert state["risk_analysis"].summary == "analysis-2 summary"
    assert state["current_stage"] == WorkflowStage.RISK_ANALYSIS

    state.update(workflow_nodes.analyse_automation(state))
    assert state["automation_analysis"].summary == "analysis-3 summary"
    assert state["current_stage"] == WorkflowStage.AUTOMATION_ANALYSIS

    state.update(workflow_nodes.synthesise_results(state))
    assert state["final_analysis"].summary == "analysis-4 summary"
    assert state["current_stage"] == WorkflowStage.FINAL_SYNTHESIS

    state.update(workflow_nodes.complete_workflow(state))
    assert state["status"] == WorkflowStatus.COMPLETED
    assert state["current_stage"] == WorkflowStage.COMPLETED
    assert state["completed_at"] == FIXED_TIME


def test_validation_normalises_filters_and_preserves_existing_errors() -> None:
    update = nodes().validate_input(workflow_input(
        project_id=" project-1 ",
        question=" question ",
        document_id_filters=[" doc-1 ", "doc-2"],
        errors=["earlier warning"],
    ))
    assert update["project_id"] == "project-1"
    assert update["question"] == "question"
    assert update["document_id_filters"] == ["doc-1", "doc-2"]
    assert update["errors"] == ["earlier warning"]


def test_multiple_document_filters_are_queried_and_globally_assembled() -> None:
    rag = FakeRAGService()
    workflow_nodes = nodes(rag=rag)
    state = workflow_input(document_id_filters=["doc-1", "doc-2"], top_k=2)
    state.update(workflow_nodes.validate_input(state))
    state.update(workflow_nodes.retrieve_evidence(state))

    assert [call["document_id"] for call in rag.calls] == ["doc-1", "doc-2"]
    assert state["rag_result"].retrieval.result_count == 2
    assert state["rag_result"].context.source_count == 2
    assert "[Source 1]" in state["rag_result"].context.combined_context
    assert "[Source 2]" in state["rag_result"].context.combined_context


def test_insufficient_evidence_node_preserves_rag_and_clears_analysis() -> None:
    workflow_nodes = nodes()
    state = workflow_input()
    state.update(workflow_nodes.validate_input(state))
    state.update(workflow_nodes.retrieve_evidence(state))
    original_rag = state["rag_result"]
    state["process_analysis"] = FakeAnalysisService().analyze(
        "question", original_rag
    )

    state.update(workflow_nodes.insufficient_evidence(state))
    assert state["rag_result"] is original_rag
    assert state["process_analysis"] is None
    assert state["final_analysis"] is None
    assert state["status"] == WorkflowStatus.INSUFFICIENT_EVIDENCE
    assert state["completed_at"] == FIXED_TIME
