import { cn } from '@/lib/cn'
import { humanise } from '@/lib/format'
import type {
  DocumentIndexStatus,
  FindingSeverity,
  WorkflowStatus,
} from '@/types/api'

type Tone = 'neutral' | 'info' | 'success' | 'warning' | 'danger' | 'critical'

const TONES: Record<Tone, string> = {
  neutral: 'bg-navy-100 text-navy-700 ring-navy-200',
  info: 'bg-accent-500/10 text-accent-600 ring-accent-500/20',
  success: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  warning: 'bg-amber-50 text-amber-800 ring-amber-200',
  danger: 'bg-red-50 text-red-700 ring-red-200',
  critical: 'bg-red-600 text-white ring-red-700',
}

export function Chip({
  tone = 'neutral',
  children,
  className,
}: {
  tone?: Tone
  children: React.ReactNode
  className?: string
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1',
        'text-xs font-medium ring-1 ring-inset',
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}

const WORKFLOW_TONES: Record<WorkflowStatus, Tone> = {
  pending: 'neutral',
  running: 'info',
  completed: 'success',
  failed: 'danger',
  insufficient_evidence: 'warning',
  governance_blocked: 'warning',
  human_review_required: 'warning',
}

/** Business-facing wording. `insufficient_evidence` means "your documents
 *  did not cover this", which is not the same as a failure. */
const WORKFLOW_LABELS: Record<WorkflowStatus, string> = {
  pending: 'Queued',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
  insufficient_evidence: 'Not enough evidence',
  governance_blocked: 'Stopped by governance',
  human_review_required: 'Needs human review',
}

export function WorkflowStatusChip({ status }: { status: WorkflowStatus }) {
  const tone = WORKFLOW_TONES[status] ?? 'neutral'
  return (
    <Chip tone={tone}>
      {status === 'running' || status === 'pending' ? (
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
      ) : null}
      {WORKFLOW_LABELS[status] ?? humanise(status)}
    </Chip>
  )
}

const INDEX_TONES: Record<DocumentIndexStatus, Tone> = {
  pending: 'neutral',
  processing: 'info',
  indexed: 'success',
  failed: 'danger',
}

const INDEX_LABELS: Record<DocumentIndexStatus, string> = {
  pending: 'Queued',
  processing: 'Processing',
  indexed: 'Ready',
  failed: 'Failed',
}

export function IndexStatusChip({ status }: { status: DocumentIndexStatus }) {
  return (
    <Chip tone={INDEX_TONES[status] ?? 'neutral'}>
      {status === 'processing' || status === 'pending' ? (
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
      ) : null}
      {INDEX_LABELS[status] ?? humanise(status)}
    </Chip>
  )
}

const SEVERITY_TONES: Record<FindingSeverity, Tone> = {
  critical: 'critical',
  high: 'danger',
  medium: 'warning',
  low: 'info',
  informational: 'neutral',
}

export function SeverityChip({ severity }: { severity: FindingSeverity }) {
  return <Chip tone={SEVERITY_TONES[severity] ?? 'neutral'}>{humanise(severity)}</Chip>
}

export function OutcomeChip({ outcome }: { outcome: string }) {
  const tone: Tone =
    outcome === 'allowed' ? 'success' : outcome === 'denied' ? 'danger' : 'warning'
  const label =
    outcome === 'allowed'
      ? 'Allowed'
      : outcome === 'denied'
        ? 'Blocked'
        : humanise(outcome)
  return <Chip tone={tone}>{label}</Chip>
}
