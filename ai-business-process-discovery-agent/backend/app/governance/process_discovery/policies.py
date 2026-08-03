from vsl_core.constructs import Fallback, PreNode, TerminalState
from vsl_core.metrics import AssuranceBasis, F2Modification

GOVERNANCE_BLOCKED = TerminalState(
    name="GOVERNANCE_BLOCKED",
    description="Automated workflow execution was denied by a governance gate.",
    entry_conditions=("A required VSL PreNode denied a transition.",),
)
INSUFFICIENT_EVIDENCE = TerminalState(
    name="INSUFFICIENT_EVIDENCE",
    description="Available evidence is insufficient for grounded analysis.",
    entry_conditions=("Retrieved context has no usable evidence sources.",),
)
UNSUPPORTED_FINDINGS = TerminalState(
    name="UNSUPPORTED_FINDINGS",
    description="Generated findings failed an evidence-grounding invariant.",
    entry_conditions=("A governed analysis output violated an invariant.",),
)
HUMAN_REVIEW_REQUIRED = TerminalState(
    name="HUMAN_REVIEW_REQUIRED",
    description="Automation must stop until an authorised human reviews it.",
    entry_conditions=("A safety invariant requires human judgement.",),
)

# These request-level checks run before the protected LLM request (F1), but
# do not alter model logits, weights, activations, or sampling (F2=NONE).
PRE_REQUEST_ASSURANCE = AssuranceBasis(
    f1_pre_commitment=True,
    f2_modification=F2Modification.NONE,
)


def process_discovery_pre_node(monitor: object, gamma_threshold: float) -> PreNode:
    return PreNode(
        name="process_discovery_pre_node",
        description="Require scoped, usable RAG evidence before process discovery.",
        monitor=monitor,  # type: ignore[arg-type]
        assurance_basis=PRE_REQUEST_ASSURANCE,
        gamma_threshold=gamma_threshold,
        fallback=Fallback(max_retries=0, on_max_retries=GOVERNANCE_BLOCKED.name),
    )


def bottleneck_analysis_pre_node(monitor: object, gamma_threshold: float) -> PreNode:
    return PreNode(
        name="bottleneck_analysis_pre_node",
        description="Require grounded process findings before bottleneck analysis.",
        monitor=monitor,  # type: ignore[arg-type]
        assurance_basis=PRE_REQUEST_ASSURANCE,
        gamma_threshold=gamma_threshold,
        fallback=Fallback(max_retries=0, on_max_retries=GOVERNANCE_BLOCKED.name),
    )


def risk_analysis_pre_node(monitor: object, gamma_threshold: float) -> PreNode:
    return PreNode(
        name="risk_analysis_pre_node",
        description="Require admissible evidence before operational risk analysis.",
        monitor=monitor,  # type: ignore[arg-type]
        assurance_basis=PRE_REQUEST_ASSURANCE,
        gamma_threshold=gamma_threshold,
        fallback=Fallback(max_retries=0, on_max_retries=GOVERNANCE_BLOCKED.name),
    )


def automation_analysis_pre_node(monitor: object, gamma_threshold: float) -> PreNode:
    return PreNode(
        name="automation_analysis_pre_node",
        description="Require process and bottleneck evidence before automation analysis.",
        monitor=monitor,  # type: ignore[arg-type]
        assurance_basis=PRE_REQUEST_ASSURANCE,
        gamma_threshold=gamma_threshold,
        fallback=Fallback(max_retries=0, on_max_retries=HUMAN_REVIEW_REQUIRED.name),
    )


def final_synthesis_pre_node(monitor: object, gamma_threshold: float) -> PreNode:
    return PreNode(
        name="final_synthesis_pre_node",
        description="Require complete invariant-verified analyses before synthesis.",
        monitor=monitor,  # type: ignore[arg-type]
        assurance_basis=PRE_REQUEST_ASSURANCE,
        gamma_threshold=gamma_threshold,
        fallback=Fallback(max_retries=0, on_max_retries=GOVERNANCE_BLOCKED.name),
    )
