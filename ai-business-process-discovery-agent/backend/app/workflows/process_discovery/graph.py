import logging
from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from vsl_langgraph import gated_node

from app.governance.process_discovery.gates import (
    ProcessDiscoveryGovernanceGates,
)
from app.governance.process_discovery.ledger import (
    ProcessDiscoveryGovernanceLedger,
)
from app.governance.process_discovery.models import (
    GovernanceStage,
    GovernanceStatus,
)
from app.llm.service import AnalysisService
from app.rag.service import RAGService
from app.workflows.process_discovery.models import WorkflowStage, WorkflowStatus
from app.workflows.process_discovery.nodes import ProcessDiscoveryNodes
from app.workflows.process_discovery.routing import (
    route_after_governed_node,
    route_after_retrieval,
    route_after_validation,
)
from app.workflows.process_discovery.state import ProcessDiscoveryState

logger = logging.getLogger(__name__)

StateNode = Callable[[ProcessDiscoveryState], ProcessDiscoveryState]


def build_process_discovery_graph(
    rag_service: RAGService,
    analysis_service: AnalysisService,
    governance_gates: ProcessDiscoveryGovernanceGates,
    governance_ledger: ProcessDiscoveryGovernanceLedger,
) -> CompiledStateGraph:
    """Build a VSL-native governed graph from injected runtime dependencies."""
    nodes = ProcessDiscoveryNodes(
        rag_service,
        analysis_service,
        governance_ledger,
    )
    graph = StateGraph(ProcessDiscoveryState)

    graph.add_node("validate_input", nodes.validate_input)
    graph.add_node("retrieve_evidence", nodes.retrieve_evidence)
    graph.add_node(
        "discover_process",
        gated_node(
            governance_gates.process_discovery,
            _record_allowed(
                nodes.discover_process,
                governance_ledger,
                node_name="discover_process",
                construct_name="process_discovery_pre_node",
                construct_type="pre_node",
                governance_stage=GovernanceStage.PROCESS_DISCOVERY,
            ),
        ),
    )
    graph.add_node(
        "validate_evidence_reference_invariant",
        gated_node(
            governance_gates.evidence_reference_invariant,
            _record_invariant_allowed(
                governance_ledger,
                node_name="validate_evidence_reference_invariant",
                construct_name="evidence_reference_invariant",
                governance_stage=GovernanceStage.PROCESS_INVARIANT,
            ),
        ),
    )
    graph.add_node(
        "validate_process_analysis_invariant",
        gated_node(
            governance_gates.process_analysis_invariant,
            _record_invariant_allowed(
                governance_ledger,
                node_name="validate_process_analysis_invariant",
                construct_name="process_analysis_invariant",
                governance_stage=GovernanceStage.PROCESS_INVARIANT,
            ),
        ),
    )
    graph.add_node(
        "analyse_bottlenecks",
        gated_node(
            governance_gates.bottleneck_analysis,
            _record_allowed(
                nodes.analyse_bottlenecks,
                governance_ledger,
                node_name="analyse_bottlenecks",
                construct_name="bottleneck_analysis_pre_node",
                construct_type="pre_node",
                governance_stage=GovernanceStage.BOTTLENECK_ANALYSIS,
            ),
        ),
    )
    graph.add_node(
        "validate_bottleneck_analysis_invariant",
        gated_node(
            governance_gates.bottleneck_analysis_invariant,
            _record_invariant_allowed(
                governance_ledger,
                node_name="validate_bottleneck_analysis_invariant",
                construct_name="bottleneck_analysis_invariant",
                governance_stage=GovernanceStage.BOTTLENECK_INVARIANT,
            ),
        ),
    )
    graph.add_node(
        "analyse_risks",
        gated_node(
            governance_gates.risk_analysis,
            _record_allowed(
                nodes.analyse_risks,
                governance_ledger,
                node_name="analyse_risks",
                construct_name="risk_analysis_pre_node",
                construct_type="pre_node",
                governance_stage=GovernanceStage.RISK_ANALYSIS,
            ),
        ),
    )
    graph.add_node(
        "validate_risk_analysis_invariant",
        gated_node(
            governance_gates.risk_scope_invariant,
            _record_invariant_allowed(
                governance_ledger,
                node_name="validate_risk_analysis_invariant",
                construct_name="risk_scope_invariant",
                governance_stage=GovernanceStage.RISK_INVARIANT,
            ),
        ),
    )
    graph.add_node(
        "analyse_automation",
        gated_node(
            governance_gates.automation_analysis,
            _record_allowed(
                nodes.analyse_automation,
                governance_ledger,
                node_name="analyse_automation",
                construct_name="automation_analysis_pre_node",
                construct_type="pre_node",
                governance_stage=GovernanceStage.AUTOMATION_ANALYSIS,
            ),
        ),
    )
    graph.add_node(
        "validate_automation_analysis_invariant",
        gated_node(
            governance_gates.automation_safety_invariant,
            _record_invariant_allowed(
                governance_ledger,
                node_name="validate_automation_analysis_invariant",
                construct_name="automation_safety_invariant",
                governance_stage=GovernanceStage.AUTOMATION_INVARIANT,
            ),
        ),
    )
    graph.add_node(
        "synthesise_results",
        gated_node(
            governance_gates.final_synthesis,
            _record_allowed(
                nodes.synthesise_results,
                governance_ledger,
                node_name="synthesise_results",
                construct_name="final_synthesis_pre_node",
                construct_type="pre_node",
                governance_stage=GovernanceStage.FINAL_SYNTHESIS,
            ),
        ),
    )
    graph.add_node(
        "validate_final_analysis_invariant",
        gated_node(
            governance_gates.final_analysis_invariant,
            _record_invariant_allowed(
                governance_ledger,
                node_name="validate_final_analysis_invariant",
                construct_name="final_analysis_invariant",
                governance_stage=GovernanceStage.FINAL_INVARIANT,
            ),
        ),
    )
    graph.add_node("complete_workflow", nodes.complete_workflow)
    graph.add_node("fail_workflow", nodes.fail_workflow)
    graph.add_node("insufficient_evidence", nodes.insufficient_evidence)
    graph.add_node("governance_blocked", nodes.governance_blocked)

    graph.add_edge(START, "validate_input")
    graph.add_conditional_edges(
        "validate_input",
        route_after_validation,
        {
            "continue": "retrieve_evidence",
            "failed": "fail_workflow",
            "terminal": END,
        },
    )
    graph.add_conditional_edges(
        "retrieve_evidence",
        route_after_retrieval,
        {
            "continue": "discover_process",
            "failed": "fail_workflow",
            "insufficient_evidence": "insufficient_evidence",
        },
    )
    _add_governed_route(
        graph,
        "discover_process",
        "validate_evidence_reference_invariant",
    )
    _add_governed_route(
        graph,
        "validate_evidence_reference_invariant",
        "validate_process_analysis_invariant",
    )
    _add_governed_route(
        graph,
        "validate_process_analysis_invariant",
        "analyse_bottlenecks",
    )
    _add_governed_route(
        graph,
        "analyse_bottlenecks",
        "validate_bottleneck_analysis_invariant",
    )
    _add_governed_route(
        graph,
        "validate_bottleneck_analysis_invariant",
        "analyse_risks",
    )
    _add_governed_route(
        graph,
        "analyse_risks",
        "validate_risk_analysis_invariant",
    )
    _add_governed_route(
        graph,
        "validate_risk_analysis_invariant",
        "analyse_automation",
    )
    _add_governed_route(
        graph,
        "analyse_automation",
        "validate_automation_analysis_invariant",
    )
    _add_governed_route(
        graph,
        "validate_automation_analysis_invariant",
        "synthesise_results",
    )
    _add_governed_route(
        graph,
        "synthesise_results",
        "validate_final_analysis_invariant",
    )
    _add_governed_route(
        graph,
        "validate_final_analysis_invariant",
        "complete_workflow",
    )

    graph.add_edge("complete_workflow", END)
    graph.add_edge("fail_workflow", END)
    graph.add_edge("insufficient_evidence", END)
    graph.add_edge("governance_blocked", END)
    return graph.compile()


def _add_governed_route(
    graph: StateGraph,
    source: str,
    allowed: str,
) -> None:
    graph.add_conditional_edges(
        source,
        route_after_governed_node,
        {
            "allowed": allowed,
            "failed": "fail_workflow",
            "governance_blocked": "governance_blocked",
        },
    )


def _record_allowed(
    node: StateNode,
    ledger: ProcessDiscoveryGovernanceLedger,
    *,
    node_name: str,
    construct_name: str,
    construct_type: str,
    governance_stage: GovernanceStage,
) -> StateNode:
    def recorded(state: ProcessDiscoveryState) -> ProcessDiscoveryState:
        try:
            decision = ledger.record_allowed(
                state,
                node_name=node_name,
                construct_name=construct_name,
                construct_type=construct_type,
            )
        except Exception:
            logger.exception(
                "Governance ledger recording failed before %s", node_name
            )
            return _ledger_failure(state)
        update = node(state)
        return {
            **update,
            "governance_status": GovernanceStatus.ALLOWED,
            "governance_stage": governance_stage,
            "governance_decisions": [
                *state.get("governance_decisions", []),
                decision,
            ],
        }

    return recorded


def _record_invariant_allowed(
    ledger: ProcessDiscoveryGovernanceLedger,
    *,
    node_name: str,
    construct_name: str,
    governance_stage: GovernanceStage,
) -> StateNode:
    def recorded(state: ProcessDiscoveryState) -> ProcessDiscoveryState:
        try:
            decision = ledger.record_allowed(
                state,
                node_name=node_name,
                construct_name=construct_name,
                construct_type="invariant",
            )
        except Exception:
            logger.exception(
                "Governance ledger recording failed during %s", node_name
            )
            return _ledger_failure(state)
        return {
            "governance_status": GovernanceStatus.ALLOWED,
            "governance_stage": governance_stage,
            "governance_decisions": [
                *state.get("governance_decisions", []),
                decision,
            ],
        }

    return recorded


def _ledger_failure(
    state: ProcessDiscoveryState,
) -> ProcessDiscoveryState:
    return {
        "status": WorkflowStatus.FAILED,
        "current_stage": WorkflowStage.FAILED,
        "errors": [
            *state.get("errors", []),
            "Governance ledger recording failed.",
        ],
    }
