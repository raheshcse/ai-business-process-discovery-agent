import asyncio
from dataclasses import replace
from typing import Any, TypedDict

import pytest
from langgraph.graph import END, START, StateGraph
from vsl_core.conformance.suite import run_conformance_suite
from vsl_core.constructs import Invariant, PreNode
from vsl_core.exceptions import AutomationDeniedException, InvariantViolation
from vsl_core.metrics import AssuranceBasis, F2Modification, GammaEstimate
from vsl_langgraph import LangGraphAdapter, gated_node, route_on_denial

from app.governance.process_discovery import (
    ProcessDiscoveryGovernanceConfig,
    build_process_discovery_governance,
)

ASSURANCE = AssuranceBasis(
    f1_pre_commitment=True,
    f2_modification=F2Modification.NONE,
)


def run(coro: Any) -> Any:
    return asyncio.run(coro)


def test_langgraph_adapter_passes_vsl_core_conformance_suite() -> None:
    assert run_conformance_suite(LangGraphAdapter()) == []


def test_compiled_pre_node_passes_and_denies_at_configured_gamma() -> None:
    async def monitor(value: dict[str, float]) -> GammaEstimate:
        return GammaEstimate(gamma_hat=value["gamma"])

    gate = LangGraphAdapter().compile_pre_node(PreNode(
        name="test_pre_node",
        description="Test deterministic Gamma threshold.",
        monitor=monitor,
        assurance_basis=ASSURANCE,
        gamma_threshold=1.1,
    ))
    run(gate({"gamma": 2.0}))
    with pytest.raises(AutomationDeniedException):
        run(gate({"gamma": 0.1}))


class GateState(TypedDict, total=False):
    gamma: float
    protected_ran: bool
    vsl_denial: object


def test_pre_node_denies_before_protected_node_executes() -> None:
    async def monitor(state: GateState) -> GammaEstimate:
        return GammaEstimate(gamma_hat=state["gamma"])

    gate = LangGraphAdapter().compile_pre_node(PreNode(
        name="blocking_pre_node",
        description="Block low Gamma before the side effect.",
        monitor=monitor,
        assurance_basis=ASSURANCE,
        gamma_threshold=1.1,
    ))
    side_effects = {"count": 0}

    def protected(state: GateState) -> dict[str, bool]:
        side_effects["count"] += 1
        return {"protected_ran": True}

    graph = StateGraph(GateState)
    graph.add_node("protected", gated_node(gate, protected))
    graph.add_node("blocked", lambda state: {})
    graph.add_node("allowed", lambda state: {})
    graph.add_edge(START, "protected")
    graph.add_conditional_edges(
        "protected", route_on_denial("blocked", "allowed")
    )
    graph.add_edge("blocked", END)
    graph.add_edge("allowed", END)
    result = run(graph.compile().ainvoke({"gamma": 0.1}))

    assert side_effects["count"] == 0
    assert result.get("protected_ran") is None
    assert isinstance(result["vsl_denial"], AutomationDeniedException)


def test_compiled_invariant_raises_specific_violation() -> None:
    async def rule(value: dict[str, bool]) -> bool:
        return value["valid"]

    gate = LangGraphAdapter().compile_invariant(Invariant(
        name="test_invariant",
        description="Reject invalid output.",
        rule=rule,
        assurance_basis=ASSURANCE,
    ))
    run(gate({"valid": True}))
    with pytest.raises(InvariantViolation):
        run(gate({"valid": False}))


def test_compiled_governance_gates_are_reusable_without_state() -> None:
    gates = build_process_discovery_governance(
        ProcessDiscoveryGovernanceConfig(minimum_evidence_score=0.5)
    )
    assert gates.process_discovery is gates.process_discovery
    first = build_process_discovery_governance()
    second = build_process_discovery_governance()
    assert first.process_discovery is not second.process_discovery
    assert first.invariants.evidence_reference.name == (
        second.invariants.evidence_reference.name
    )
    assert {
        first.invariants.evidence_reference.name,
        first.invariants.process_analysis.name,
        first.invariants.bottleneck_analysis.name,
        first.invariants.risk_scope.name,
        first.invariants.automation_safety.name,
        first.invariants.final_analysis.name,
    } == {
        "evidence_reference_invariant",
        "process_analysis_invariant",
        "bottleneck_analysis_invariant",
        "risk_scope_invariant",
        "automation_safety_invariant",
        "final_analysis_invariant",
    }


def denying_gate(name: str) -> Any:
    async def monitor(state: dict[str, Any]) -> GammaEstimate:
        return GammaEstimate(gamma_hat=0.0)

    return LangGraphAdapter().compile_pre_node(PreNode(
        name=name,
        description="Deterministic test denial.",
        monitor=monitor,
        assurance_basis=ASSURANCE,
        gamma_threshold=1.1,
    ))


def gates_with_denial(field: str, construct_name: str) -> Any:
    gates = build_process_discovery_governance()
    return replace(gates, **{field: denying_gate(construct_name)})
