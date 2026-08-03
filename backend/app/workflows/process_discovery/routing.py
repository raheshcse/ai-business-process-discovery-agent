from typing import Literal

from vsl_langgraph import route_on_denial

from app.workflows.process_discovery.models import WorkflowStatus
from app.workflows.process_discovery.state import ProcessDiscoveryState

FailureRoute = Literal["continue", "failed", "terminal"]
RetrievalRoute = Literal["continue", "failed", "insufficient_evidence"]
GovernedRoute = Literal["allowed", "failed", "governance_blocked"]


def route_after_validation(state: ProcessDiscoveryState) -> FailureRoute:
    if state.get("terminal_state_name") is not None:
        return "terminal"
    return (
        "failed"
        if state.get("status") == WorkflowStatus.FAILED
        else "continue"
    )


def route_after_retrieval(state: ProcessDiscoveryState) -> RetrievalRoute:
    status = state.get("status")
    if status == WorkflowStatus.FAILED:
        return "failed"
    if status == WorkflowStatus.INSUFFICIENT_EVIDENCE:
        return "insufficient_evidence"
    return "continue"


def route_after_analysis(state: ProcessDiscoveryState) -> FailureRoute:
    return (
        "failed"
        if state.get("status") == WorkflowStatus.FAILED
        else "continue"
    )


def route_after_governed_node(state: ProcessDiscoveryState) -> GovernedRoute:
    denial_route = route_on_denial("governance_blocked", "allowed")(state)
    if denial_route == "governance_blocked":
        return "governance_blocked"
    if state.get("status") == WorkflowStatus.FAILED:
        return "failed"
    return "allowed"
