/**
 * TypeScript mirrors of the backend Pydantic schemas.
 *
 * Every type here corresponds to a named schema in the FastAPI OpenAPI
 * document at `/openapi.json`. Field names and optionality match the
 * backend exactly -- when the backend changes, this file is the single
 * place the frontend needs to follow.
 */

/* ---------------------------------------------------------------- Health */

export interface HealthResponse {
  status: string
  application: string
  version: string
  environment: string
  llm_provider: string
  llm_model: string
  embedding_provider: string
  /** False when retrieval scores are not semantic, which makes the
   *  evidence governance gate unreliable. The UI warns on this. */
  embeddings_are_semantic: boolean
  minimum_evidence_score: number
}

/* -------------------------------------------------------------- Projects */

export interface Project {
  id: string
  name: string
  client_name: string | null
  department: string | null
  industry: string | null
  objective: string
  status: string
  created_at: string
  updated_at: string
}

export interface ProjectCreate {
  name: string
  client_name?: string | null
  department?: string | null
  industry?: string | null
  objective: string
  status?: string
}

/** Every field optional; the backend rejects unknown keys (`extra=forbid`). */
export type ProjectUpdate = Partial<ProjectCreate>

export const PROJECT_STATUSES = [
  'draft',
  'active',
  'on_hold',
  'completed',
  'archived',
] as const

export type ProjectStatus = (typeof PROJECT_STATUSES)[number]

/* ------------------------------------------------------------- Documents */

export type DocumentIndexStatus = 'pending' | 'processing' | 'indexed' | 'failed'

export interface ProjectDocument {
  id: string
  project_id: string
  original_filename: string
  content_type: string
  file_extension: string
  size_bytes: number
  created_at: string
  index_status: DocumentIndexStatus
  index_error: string | null
  indexed_at: string | null
  page_count: number | null
  word_count: number | null
  character_count: number | null
  chunk_count: number | null
  detected_document_type: string | null
}

/* -------------------------------------------------------------- Analysis */

export type FindingCategory =
  | 'process'
  | 'bottleneck'
  | 'control'
  | 'risk'
  | 'data'
  | 'role'
  | 'technology'
  | 'opportunity'
  | 'other'

export type FindingSeverity =
  | 'informational'
  | 'low'
  | 'medium'
  | 'high'
  | 'critical'

export interface AnalysisFinding {
  title: string
  description: string
  category: FindingCategory
  severity: FindingSeverity
  /** `Source N` markers, matching `Citation.source_id`. */
  evidence_source_ids: string[]
  recommendation: string
}

export interface Assumption {
  description: string
  reason: string
}

export interface BusinessAnalysisResult {
  summary: string
  findings: AnalysisFinding[]
  assumptions: Assumption[]
  insufficient_evidence: string[]
  confidence: number
  provider_name: string | null
  model_name: string | null
}

export interface Citation {
  source_id: string
  document_id: string
  chunk_id: string
  chunk_index: number
  score: number
  filename: string | null
}

export type WorkflowStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'insufficient_evidence'
  | 'governance_blocked'
  | 'human_review_required'

export type WorkflowStage =
  | 'validation'
  | 'retrieval'
  | 'process_discovery'
  | 'bottleneck_analysis'
  | 'risk_analysis'
  | 'automation_analysis'
  | 'final_synthesis'
  | 'completed'
  | 'failed'
  | 'governance_blocked'
  | 'human_review_required'

export interface AnalysisRunSummary {
  id: string
  project_id: string
  question: string
  status: WorkflowStatus
  current_stage: WorkflowStage
  governance_status: string
  terminal_state_name: string | null
  human_review_required: boolean
  source_count: number
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export interface AnalysisRunDetail extends AnalysisRunSummary {
  top_k: number
  minimum_similarity_score: number | null
  document_id_filters: string[]
  governance_stage: string
  errors: string[]
  denial_summary: Record<string, unknown> | null
  process_analysis: BusinessAnalysisResult | null
  bottleneck_analysis: BusinessAnalysisResult | null
  risk_analysis: BusinessAnalysisResult | null
  automation_analysis: BusinessAnalysisResult | null
  final_analysis: BusinessAnalysisResult | null
  citations: Citation[]
  retrieval_provider: string | null
  retrieval_model: string | null
  retrieved_count: number
  context_truncated: boolean
}

export interface AnalysisRunCreate {
  question: string
  top_k?: number | null
  minimum_similarity_score?: number | null
  document_id_filters?: string[]
}

/* ------------------------------------------------------------ Governance */

export interface GovernanceEvent {
  sequence: number
  decision_id: string
  node_name: string
  construct_name: string
  construct_type: string
  outcome: string
  source_count: number
  confidence: number | null
  terminal_state_name: string | null
  recorded_at: string
}

export interface LedgerEntry {
  entry_id: string
  sequence: number
  entry_type: string
  identity_key: string
  instance_id: string | null
  decision_id: string | null
  caused_by: string | null
  payload: Record<string, unknown>
  timestamp: number
  prev_hash: string
  entry_hash: string
}

export interface LedgerAuditCheck {
  name: string
  label: string
  passed: boolean
  explanation: string
  violation_count: number
}

export interface GovernanceReport {
  analysis_run_id: string
  project_id: string
  question: string
  workflow_status: string
  governance_status: string
  governance_stage: string
  terminal_state_name: string | null
  human_review_required: boolean
  denial_summary: Record<string, unknown> | null
  errors: string[]
  decisions: GovernanceEvent[]
  ledger_entries: LedgerEntry[]
  chain_verified: boolean
  checkpoint_sequence: number | null
  checkpoint_hash: string | null
  audit_checks: LedgerAuditCheck[]
  certificate_issued: boolean
  certificate_hash: string | null
  certificate_note: string | null
}

export interface GovernanceConstruct {
  name: string
  kind: string
  stage: string
  description: string
  on_violation: string | null
}

export interface GovernanceCatalogue {
  gamma_threshold: number
  minimum_evidence_score: number
  minimum_process_findings: number
  pre_nodes: GovernanceConstruct[]
  invariants: GovernanceConstruct[]
  terminal_states: GovernanceConstruct[]
}

/* ------------------------------------------------------------- Dashboard */

export interface SeverityBreakdown {
  critical: number
  high: number
  medium: number
  low: number
  informational: number
}

export interface RecentActivityItem {
  kind: 'project' | 'document' | 'analysis'
  title: string
  subtitle: string | null
  project_id: string | null
  project_name: string | null
  analysis_run_id: string | null
  status: string | null
  occurred_at: string
}

export interface DashboardSummary {
  project_count: number
  document_count: number
  indexed_document_count: number
  documents_pending_count: number
  documents_failed_count: number
  analysis_total_count: number
  analysis_completed_count: number
  analysis_running_count: number
  analysis_failed_count: number
  analysis_blocked_count: number
  analysis_human_review_count: number
  risk_finding_count: number
  risk_severity: SeverityBreakdown
  automation_opportunity_count: number
  bottleneck_finding_count: number
  recent_activity: RecentActivityItem[]
}
