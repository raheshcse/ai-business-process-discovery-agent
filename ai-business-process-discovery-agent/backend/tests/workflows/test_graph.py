import asyncio
from typing import Any

import pytest
from vsl_core.ledger import VerbaLedger

from app.governance.process_discovery import build_process_discovery_governance
from app.governance.process_discovery.ledger import (
    ProcessDiscoveryGovernanceLedger,
)
from app.workflows.process_discovery import (
    WorkflowStage,
    WorkflowStatus,
    build_process_discovery_graph,
)
from tests.workflows.helpers import (
    FakeAnalysisService,
    FakeRAGService,
    rag_result,
    workflow_input,
)


def build(
    rag: FakeRAGService | None = None,
    analysis: FakeAnalysisService | None = None,
) -> Any:
    return build_process_discovery_graph(
        rag or FakeRAGService(),  # type: ignore[arg-type]
        analysis or FakeAnalysisService(),  # type: ignore[arg-type]
        build_process_discovery_governance(),
        ProcessDiscoveryGovernanceLedger(VerbaLedger()),
    )


def invoke(graph: Any, value: dict[str, Any]) -> dict[str, Any]:
    return asyncio.run(graph.ainvoke(value))


def test_successful_graph_completes_and_stores_every_analysis() -> None:
    rag = FakeRAGService()
    analysis = FakeAnalysisService()
    result = invoke(build(rag, analysis), workflow_input())

    assert result["status"] == WorkflowStatus.COMPLETED
    assert result["current_stage"] == WorkflowStage.COMPLETED
    assert result["process_analysis"].summary == "analysis-0 summary"
    assert result["bottleneck_analysis"].summary == "analysis-1 summary"
    assert result["risk_analysis"].summary == "analysis-2 summary"
    assert result["automation_analysis"].summary == "analysis-3 summary"
    assert result["final_analysis"].summary == "analysis-4 summary"
    assert result["started_at"] is not None
    assert result["completed_at"] is not None
    assert result["errors"] == []
    assert len(result["governance_decisions"]) == 11
    assert len(rag.calls) == 1
    assert len(analysis.calls) == 5
    assert all(call["context"] is result["rag_result"] for call in analysis.calls)


def test_graph_executes_nodes_in_the_declared_order() -> None:
    graph = build()

    async def collect() -> list[dict[str, Any]]:
        return [
            event
            async for event in graph.astream(
                workflow_input(), stream_mode="updates"
            )
        ]

    events = asyncio.run(collect())
    assert [next(iter(event)) for event in events] == [
        "validate_input",
        "retrieve_evidence",
        "discover_process",
        "validate_evidence_reference_invariant",
        "validate_process_analysis_invariant",
        "analyse_bottlenecks",
        "validate_bottleneck_analysis_invariant",
        "analyse_risks",
        "validate_risk_analysis_invariant",
        "analyse_automation",
        "validate_automation_analysis_invariant",
        "synthesise_results",
        "validate_final_analysis_invariant",
        "complete_workflow",
    ]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"project_id": " "}, "project_id"),
        ({"question": " "}, "question"),
        ({"top_k": 0}, "top_k"),
        ({"minimum_similarity_score": 1.1}, "minimum_similarity_score"),
    ],
)
def test_validation_failure_routes_to_failed(
    overrides: dict[str, Any], message: str
) -> None:
    rag = FakeRAGService()
    analysis = FakeAnalysisService()
    result = invoke(build(rag, analysis), workflow_input(**overrides))

    assert result["status"] == WorkflowStatus.FAILED
    assert result["current_stage"] == WorkflowStage.FAILED
    assert result["completed_at"] is not None
    assert message in result["errors"][-1]
    assert rag.calls == []
    assert analysis.calls == []


def test_no_retrieval_results_routes_to_insufficient_evidence() -> None:
    rag = FakeRAGService(result=rag_result(text=""))
    analysis = FakeAnalysisService()
    result = invoke(build(rag, analysis), workflow_input())

    assert result["status"] == WorkflowStatus.INSUFFICIENT_EVIDENCE
    assert result["current_stage"] == WorkflowStage.RETRIEVAL
    assert result["terminal_state_name"] == "INSUFFICIENT_EVIDENCE"
    assert result["rag_result"].retrieval.result_count == 0
    assert result["final_analysis"] is None
    assert result["completed_at"] is not None
    assert analysis.calls == []


def test_minimum_score_filter_can_produce_insufficient_evidence() -> None:
    rag = FakeRAGService(score=0.4)
    result = invoke(
        build(rag),
        workflow_input(minimum_similarity_score=0.8),
    )
    assert result["status"] == WorkflowStatus.INSUFFICIENT_EVIDENCE
    assert rag.calls[0]["minimum_score"] == 0.8


def test_retrieval_failure_routes_to_failed_and_preserves_errors() -> None:
    result = invoke(
        build(FakeRAGService(fail=True)),
        workflow_input(errors=["existing error"]),
    )
    assert result["status"] == WorkflowStatus.FAILED
    assert result["completed_at"] is not None
    assert result["errors"][0] == "existing error"
    assert "retrieval failed" in result["errors"][-1].lower()
    assert "sensitive retrieval detail" not in result["errors"][-1]


@pytest.mark.parametrize("fail_on", [0, 1, 2, 3])
def test_each_analysis_stage_failure_routes_to_failed(fail_on: int) -> None:
    analysis = FakeAnalysisService(fail_on=fail_on)
    result = invoke(build(analysis=analysis), workflow_input())

    assert result["status"] == WorkflowStatus.FAILED
    assert result["current_stage"] == WorkflowStage.FAILED
    assert result["completed_at"] is not None
    assert len(analysis.calls) == fail_on + 1
    assert "provider was unavailable" in result["errors"][-1]
    assert "sensitive provider detail" not in result["errors"][-1]


def test_synthesis_failure_routes_to_failed() -> None:
    analysis = FakeAnalysisService(fail_on=4)
    result = invoke(build(analysis=analysis), workflow_input())
    assert result["status"] == WorkflowStatus.FAILED
    assert result["final_analysis"] is None
    assert "Final synthesis failed" in result["errors"][-1]
    assert result["completed_at"] is not None


def test_injected_filters_are_forwarded_to_rag_service() -> None:
    rag = FakeRAGService()
    invoke(
        build(rag=rag),
        workflow_input(
            document_id_filters=["doc-9"],
            metadata_filters={"department": "finance"},
            top_k=3,
            minimum_similarity_score=0.7,
        ),
    )
    assert rag.calls == [{
        "query": "How does invoice approval work?",
        "document_id": "doc-9",
        "top_k": 3,
        "metadata_filters": {"department": "finance"},
        "minimum_score": 0.7,
    }]


def test_compiled_graph_can_be_reused_without_state_leaking() -> None:
    rag = FakeRAGService()
    analysis = FakeAnalysisService()
    graph = build(rag, analysis)
    first = invoke(graph, workflow_input(project_id="project-1"))
    second = invoke(graph, workflow_input(project_id="project-1"))

    assert first["workflow_id"] != second["workflow_id"]
    assert first["governance_instance_id"] != second["governance_instance_id"]
    assert first["errors"] == []
    assert second["errors"] == []
    assert len(first["governance_decisions"]) == 11
    assert len(second["governance_decisions"]) == 11
    assert first["process_analysis"] is not second["process_analysis"]
    assert len(rag.calls) == 2
    assert len(analysis.calls) == 10
