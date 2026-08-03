# VSL-native process discovery

## Architecture

The Process Discovery workflow uses four distinct layers:

```text
vsl-core governance specification
        ↓
vsl-langgraph compiled gates
        ↓
LangGraph orchestration
        ↓
injected RAGService and AnalysisService
```

`vsl-core` supplies the governance vocabulary and enforcement constructs:
`PreNode`, `Invariant`, `TerminalState`, `GammaEstimate`,
`AssuranceBasis`, governance exceptions, and `VerbaLedger`.
`vsl-langgraph` supplies the conformant `LangGraphAdapter`, `gated_node`,
and `route_on_denial` integration. LangGraph remains the workflow
orchestration engine. The existing RAG and LLM services remain responsible
for retrieval and structured analysis.

The graph builder requires injected `RAGService`, `AnalysisService`,
`ProcessDiscoveryGovernanceGates`, and
`ProcessDiscoveryGovernanceLedger` objects. The ledger service wraps an
injected `VerbaLedger`; the graph does not construct either dependency.
Compiled gates, providers, adapters, ledgers, database sessions, and vector
stores are not stored in workflow state.

## Governed flow

Each hosted or local LLM action has a compiled PreNode immediately before
the protected node:

- `process_discovery_pre_node`
- `bottleneck_analysis_pre_node`
- `risk_analysis_pre_node`
- `automation_analysis_pre_node`
- `final_synthesis_pre_node`

Each analytical output is checked before downstream use:

- `evidence_reference_invariant` validates process findings.
- `process_analysis_invariant` validates process-analysis scope.
- `bottleneck_analysis_invariant` validates bottleneck findings.
- `risk_scope_invariant` limits findings to operational/control risk and
  rejects explicit legal conclusions.
- `automation_safety_invariant` requires appropriate human review and
  rejects unsupported autonomous execution.
- `final_analysis_invariant` validates final grounding, citations,
  assumptions, insufficient-evidence reporting, and unresolved denials.

The deterministic monitors inspect only candidate workflow state. They do
not call an LLM and have no side effects. Evidence readiness includes:
usable context, source count, configured score threshold, document scope,
and citation `metadata["project_id"]` matching the requested project.
The Gamma values are deterministic readiness proxies; they are not
measurements of model correctness or guarantees about the business domain.

The invariant checks establish structural grounding—for example, whether a
finding cites an available source identifier. They cannot independently
prove that natural-language content faithfully represents a document.
Governance does not guarantee that the model or business analysis is
correct.

## Routing and terminal states

A VSL denial is captured by the official `gated_node` helper in the runtime
`vsl_denial` field. Conditional routing sends it to `governance_blocked`,
which creates a separate serialisable denial summary and terminates the
automated path.

Terminal states are:

- `GOVERNANCE_BLOCKED`
- `INSUFFICIENT_EVIDENCE`
- `UNSUPPORTED_FINDINGS`
- `HUMAN_REVIEW_REQUIRED`

Technical failures, insufficient evidence, governance blocking, human
review, and successful completion remain distinct workflow statuses. A
terminal state stops automated transitions for that workflow invocation;
the implementation does not claim every denial is permanently irreversible.

There is currently no approval UI or re-enablement API. The workflow never
calls `Instance._re_enable()`. Any future re-enablement must use
`vsl_core.governance.request_re_enablement()` with appropriate authority and
evidence.

## Ledger

An injected `VerbaLedger` receives governance events for:

- monitor outcomes;
- PreNode allow/denial decisions;
- invariant verification;
- terminal-state entry;
- human-review requirements.

Entries correlate by workflow and governance instance identifiers. Payloads
contain only safe metadata such as node name, outcome, source count,
confidence when available, and terminal-state name. They exclude document
content, prompts, API keys, embeddings, provider exceptions, and stack
traces.

The ledger is append-only and hash chained, but no external anchoring or
persistent store is configured by this workflow. The caller chooses and
injects the ledger/store lifetime.

## Assurance claims

PreNodes execute before the protected RAG-dependent LLM request, so F1
pre-commitment is true. They block or allow a request but do not modify
model logits, weights, activations, prompts, or sampling, so their declared
F2 modification is `NONE`; VSL-Core consequently derives `LOW` assurance.

Output invariants run after model generation and before downstream reliance.
They claim neither F1 model pre-commitment nor F2 modification. No component
claims `F2Modification.FULL`.

## Current adapter limitations

`vsl-langgraph` is alpha software. Its `gated_node` helper is asynchronous,
so governed graphs must use `ainvoke`/`astream`. It catches
`AutomationDeniedException` and returns it in runtime state for routing.

The adapter currently does not consume `Fallback` retry, intervention,
`delta_factor`, or `max_retries` behavior. Policy declarations retain honest
terminal intent, but this workflow does not claim retries or interventions
occur. Denials terminate safely instead.

`vsl-core` does not write ledger events automatically. This application
records them explicitly after allowed gates and in terminal denial handling.
The current adapter's compiled-gate call returns no `GammaEstimate`, so the
application cannot record the exact estimate without executing a monitor
twice or replacing the official adapter path. It records the monitor outcome
and safe decision metadata instead; it does not fabricate a Gamma value.
