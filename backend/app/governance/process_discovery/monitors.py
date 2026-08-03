import re
from dataclasses import dataclass
from typing import Any, Mapping

from vsl_core.metrics import GammaEstimate

_BLOCKED_WORKFLOW_STATUSES = {
    "failed",
    "governance_blocked",
    "human_review_required",
}
_BLOCKED_GOVERNANCE_STATUSES = {"blocked", "human_review_required"}


@dataclass(frozen=True)
class ProcessDiscoveryMonitorConfig:
    minimum_evidence_score: float = 0.5
    minimum_process_findings: int = 1


class ProcessDiscoveryMonitors:
    """Deterministic, side-effect-free readiness monitors."""

    def __init__(self, config: ProcessDiscoveryMonitorConfig) -> None:
        self._config = config

    async def process_discovery(self, state: Mapping[str, Any]) -> GammaEstimate:
        rag_result = state.get("rag_result")
        context = getattr(rag_result, "context", None)
        citations = list(getattr(context, "citations", []) or [])
        valid = (
            self._admissible(state)
            and context is not None
            and bool(getattr(context, "combined_context", "").strip())
            and int(getattr(context, "source_count", 0)) > 0
            and bool(citations)
            and self._sources_in_scope(state, citations)
            and all(
                citation.score >= self._config.minimum_evidence_score
                for citation in citations
            )
        )
        quality = min((citation.score for citation in citations), default=0.0)
        return self._estimate(valid, quality)

    async def bottleneck_analysis(self, state: Mapping[str, Any]) -> GammaEstimate:
        analysis = state.get("process_analysis")
        findings = list(getattr(analysis, "findings", []) or [])
        valid = (
            self._admissible(state)
            and analysis is not None
            and len(findings) >= self._config.minimum_process_findings
            and all(finding.evidence_source_ids for finding in findings)
        )
        return self._estimate(valid, min(len(findings), 5) / 5)

    async def risk_analysis(self, state: Mapping[str, Any]) -> GammaEstimate:
        available_sources = _available_source_ids(state)
        valid = (
            self._admissible(state)
            and state.get("process_analysis") is not None
            and bool(available_sources)
        )
        return self._estimate(valid, min(len(available_sources), 5) / 5)

    async def automation_analysis(self, state: Mapping[str, Any]) -> GammaEstimate:
        process_analysis = state.get("process_analysis")
        bottleneck_analysis = state.get("bottleneck_analysis")
        valid = (
            self._admissible(state)
            and process_analysis is not None
            and bottleneck_analysis is not None
            and bool(getattr(process_analysis, "findings", []))
            and bool(_available_source_ids(state))
        )
        return self._estimate(valid, 1.0 if valid else 0.0)

    async def final_synthesis(self, state: Mapping[str, Any]) -> GammaEstimate:
        required_results = (
            "process_analysis",
            "bottleneck_analysis",
            "risk_analysis",
            "automation_analysis",
        )
        verified = {
            decision.get("construct_name")
            for decision in state.get("governance_decisions", [])
            if decision.get("outcome") == "allowed"
        }
        required_invariants = {
            "evidence_reference_invariant",
            "process_analysis_invariant",
            "bottleneck_analysis_invariant",
            "risk_scope_invariant",
            "automation_safety_invariant",
        }
        valid = (
            self._admissible(state)
            and all(state.get(key) is not None for key in required_results)
            and required_invariants.issubset(verified)
            and bool(_available_source_ids(state))
            and state.get("vsl_denial") is None
        )
        return self._estimate(valid, 1.0 if valid else 0.0)

    @staticmethod
    def _admissible(state: Mapping[str, Any]) -> bool:
        status = getattr(state.get("status"), "value", state.get("status"))
        governance_status = getattr(
            state.get("governance_status"),
            "value",
            state.get("governance_status"),
        )
        return (
            status not in _BLOCKED_WORKFLOW_STATUSES
            and governance_status not in _BLOCKED_GOVERNANCE_STATUSES
            and state.get("terminal_state_name") is None
            and state.get("vsl_denial") is None
        )

    @staticmethod
    def _sources_in_scope(
        state: Mapping[str, Any], citations: list[Any]
    ) -> bool:
        document_ids = set(state.get("document_id_filters", []) or [])
        if document_ids and any(
            citation.document_id not in document_ids for citation in citations
        ):
            return False
        project_id = state.get("project_id")
        for citation in citations:
            source_project = citation.metadata.get("project_id")
            if source_project is None or source_project != project_id:
                return False
        return True

    @staticmethod
    def _estimate(valid: bool, quality: float) -> GammaEstimate:
        return GammaEstimate(
            gamma_hat=2.0 if valid else 0.0,
            energy_gap_estimate=max(0.0, quality),
        )


def _available_source_ids(state: Mapping[str, Any]) -> set[str]:
    rag_result = state.get("rag_result")
    context = getattr(rag_result, "context", None)
    combined = getattr(context, "combined_context", "")
    return {
        f"Source {number}"
        for number in re.findall(r"\[Source (\d+)\]", combined)
    }
