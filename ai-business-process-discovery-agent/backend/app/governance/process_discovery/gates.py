from dataclasses import dataclass

from vsl_core.conformance.protocol import CompiledGate
from vsl_langgraph import LangGraphAdapter

from app.governance.process_discovery.invariants import (
    ProcessDiscoveryInvariants,
    build_process_discovery_invariants,
)
from app.governance.process_discovery.monitors import (
    ProcessDiscoveryMonitorConfig,
    ProcessDiscoveryMonitors,
)
from app.governance.process_discovery.policies import (
    automation_analysis_pre_node,
    bottleneck_analysis_pre_node,
    final_synthesis_pre_node,
    process_discovery_pre_node,
    risk_analysis_pre_node,
)


@dataclass(frozen=True)
class ProcessDiscoveryGovernanceConfig:
    gamma_threshold: float = 1.1
    minimum_evidence_score: float = 0.5
    minimum_process_findings: int = 1


@dataclass(frozen=True)
class ProcessDiscoveryGovernanceGates:
    process_discovery: CompiledGate
    bottleneck_analysis: CompiledGate
    risk_analysis: CompiledGate
    automation_analysis: CompiledGate
    final_synthesis: CompiledGate
    evidence_reference_invariant: CompiledGate
    process_analysis_invariant: CompiledGate
    bottleneck_analysis_invariant: CompiledGate
    risk_scope_invariant: CompiledGate
    automation_safety_invariant: CompiledGate
    final_analysis_invariant: CompiledGate
    invariants: ProcessDiscoveryInvariants


def build_process_discovery_governance(
    config: ProcessDiscoveryGovernanceConfig | None = None,
    *,
    adapter: LangGraphAdapter | None = None,
) -> ProcessDiscoveryGovernanceGates:
    """Compile reusable VSL-Core policies through the VSL-LangGraph adapter."""
    resolved = config or ProcessDiscoveryGovernanceConfig()
    if resolved.gamma_threshold <= 0:
        raise ValueError("gamma_threshold must be greater than zero")
    if not 0.0 <= resolved.minimum_evidence_score <= 1.0:
        raise ValueError("minimum_evidence_score must be between 0 and 1")
    if resolved.minimum_process_findings <= 0:
        raise ValueError("minimum_process_findings must be greater than zero")

    compiler = adapter or LangGraphAdapter()
    monitors = ProcessDiscoveryMonitors(
        ProcessDiscoveryMonitorConfig(
            minimum_evidence_score=resolved.minimum_evidence_score,
            minimum_process_findings=resolved.minimum_process_findings,
        )
    )
    invariants = build_process_discovery_invariants()
    return ProcessDiscoveryGovernanceGates(
        process_discovery=compiler.compile_pre_node(
            process_discovery_pre_node(
                monitors.process_discovery, resolved.gamma_threshold
            )
        ),
        bottleneck_analysis=compiler.compile_pre_node(
            bottleneck_analysis_pre_node(
                monitors.bottleneck_analysis, resolved.gamma_threshold
            )
        ),
        risk_analysis=compiler.compile_pre_node(
            risk_analysis_pre_node(
                monitors.risk_analysis, resolved.gamma_threshold
            )
        ),
        automation_analysis=compiler.compile_pre_node(
            automation_analysis_pre_node(
                monitors.automation_analysis, resolved.gamma_threshold
            )
        ),
        final_synthesis=compiler.compile_pre_node(
            final_synthesis_pre_node(
                monitors.final_synthesis, resolved.gamma_threshold
            )
        ),
        evidence_reference_invariant=compiler.compile_invariant(
            invariants.evidence_reference
        ),
        process_analysis_invariant=compiler.compile_invariant(
            invariants.process_analysis
        ),
        bottleneck_analysis_invariant=compiler.compile_invariant(
            invariants.bottleneck_analysis
        ),
        risk_scope_invariant=compiler.compile_invariant(invariants.risk_scope),
        automation_safety_invariant=compiler.compile_invariant(
            invariants.automation_safety
        ),
        final_analysis_invariant=compiler.compile_invariant(
            invariants.final_analysis
        ),
        invariants=invariants,
    )
