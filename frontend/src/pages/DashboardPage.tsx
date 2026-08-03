import { Link } from 'react-router-dom'
import { PageShell } from '@/components/layout/PageShell'
import { Card, CardBody, CardHeader, StatCard } from '@/components/ui/Card'
import { WorkflowStatusChip } from '@/components/ui/StatusChip'
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/States'
import {
  ClockIcon,
  DashboardIcon,
  DocumentIcon,
  PlusIcon,
  ProjectsIcon,
  SparkIcon,
} from '@/components/ui/icons'
import { useDashboard } from '@/hooks/queries'
import { formatRelative, humanise } from '@/lib/format'
import type {
  DashboardSummary,
  RecentActivityItem,
  SeverityBreakdown,
  WorkflowStatus,
} from '@/types/api'

export function DashboardPage() {
  const { data, isLoading, isError, error, refetch } = useDashboard()

  return (
    <PageShell
      title="Dashboard"
      description="Portfolio view of discovery projects, evidence and governed analyses"
      actions={
        <Link
          to="/projects"
          className="inline-flex h-10 items-center gap-2 rounded-lg bg-accent-500 px-4 text-sm font-medium text-white transition-colors hover:bg-accent-600"
        >
          <PlusIcon className="h-4 w-4" />
          New project
        </Link>
      }
    >
      {isLoading ? <LoadingState label="Loading your portfolio…" /> : null}
      {isError ? <ErrorState error={error} onRetry={() => void refetch()} /> : null}
      {data ? <DashboardContent summary={data} /> : null}
    </PageShell>
  )
}

function DashboardContent({ summary }: { summary: DashboardSummary }) {
  const isEmpty = summary.project_count === 0

  if (isEmpty) {
    return (
      <EmptyState
        icon={<DashboardIcon className="h-10 w-10" />}
        title="Nothing to show yet"
        description="Create a project, upload your process documentation, and run a governed analysis. Results and audit evidence will appear here."
        action={
          <Link
            to="/projects"
            className="inline-flex h-10 items-center rounded-lg bg-accent-500 px-4 text-sm font-medium text-white hover:bg-accent-600"
          >
            Create your first project
          </Link>
        }
      />
    )
  }

  return (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Projects"
          value={summary.project_count}
          hint={`${summary.analysis_total_count} ${summary.analysis_total_count === 1 ? 'analysis' : 'analyses'} run`}
        />
        <StatCard
          label="Documents indexed"
          value={`${summary.indexed_document_count}/${summary.document_count}`}
          hint={
            summary.documents_failed_count > 0
              ? `${summary.documents_failed_count} failed to process`
              : summary.documents_pending_count > 0
                ? `${summary.documents_pending_count} still processing`
                : 'All documents ready'
          }
          tone={summary.documents_failed_count > 0 ? 'warning' : 'default'}
        />
        <StatCard
          label="Risks identified"
          value={summary.risk_finding_count}
          hint={severityHint(summary.risk_severity)}
          tone={
            summary.risk_severity.critical + summary.risk_severity.high > 0
              ? 'danger'
              : 'default'
          }
        />
        <StatCard
          label="Automation opportunities"
          value={summary.automation_opportunity_count}
          hint={`${summary.bottleneck_finding_count} bottleneck${summary.bottleneck_finding_count === 1 ? '' : 's'} found`}
          tone="success"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader
            title="Analysis status"
            description="Across every project"
          />
          <CardBody className="space-y-3">
            <StatusRow
              label="Completed"
              value={summary.analysis_completed_count}
              status="completed"
            />
            <StatusRow
              label="In progress"
              value={summary.analysis_running_count}
              status="running"
            />
            <StatusRow
              label="Needs human review"
              value={summary.analysis_human_review_count}
              status="human_review_required"
            />
            <StatusRow
              label="Stopped by governance"
              value={summary.analysis_blocked_count}
              status="governance_blocked"
            />
            <StatusRow
              label="Failed"
              value={summary.analysis_failed_count}
              status="failed"
            />
            {summary.analysis_total_count === 0 ? (
              <p className="pt-1 text-sm text-navy-500">
                No analyses have been run yet. Open a project to start one.
              </p>
            ) : null}
          </CardBody>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader
            title="Recent activity"
            description="Newest first"
            action={
              <Link
                to="/projects"
                className="text-sm font-medium text-accent-600 hover:text-accent-500"
              >
                All projects
              </Link>
            }
          />
          <CardBody className="p-0 sm:p-0">
            {summary.recent_activity.length === 0 ? (
              <div className="px-6 py-10">
                <p className="text-sm text-navy-500">Nothing has happened yet.</p>
              </div>
            ) : (
              <ul className="divide-y divide-navy-100">
                {summary.recent_activity.map((item, index) => (
                  <ActivityRow key={`${item.kind}-${index}`} item={item} />
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
      </div>
    </>
  )
}

function StatusRow({
  label,
  value,
  status,
}: {
  label: string
  value: number
  status: WorkflowStatus
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="flex min-w-0 items-center gap-2.5">
        <WorkflowStatusChip status={status} />
        <span className="truncate text-sm text-navy-600">{label}</span>
      </div>
      <span className="text-sm font-semibold tabular-nums text-navy-900">{value}</span>
    </div>
  )
}

const ACTIVITY_ICONS = {
  project: ProjectsIcon,
  document: DocumentIcon,
  analysis: SparkIcon,
} as const

function ActivityRow({ item }: { item: RecentActivityItem }) {
  const Icon = ACTIVITY_ICONS[item.kind] ?? ClockIcon
  const href = item.analysis_run_id
    ? `/analyses/${item.analysis_run_id}`
    : item.project_id
      ? `/projects/${item.project_id}`
      : null

  const content = (
    <div className="flex items-start gap-3 px-5 py-3.5 sm:px-6">
      <div className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-navy-100 text-navy-600">
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-navy-900">{item.title}</p>
        <p className="mt-0.5 truncate text-xs text-navy-500">
          {item.project_name ? `${item.project_name} · ` : ''}
          {item.subtitle}
        </p>
      </div>
      <span className="shrink-0 whitespace-nowrap text-xs text-navy-400">
        {formatRelative(item.occurred_at)}
      </span>
    </div>
  )

  return (
    <li>
      {href ? (
        <Link to={href} className="block hover:bg-navy-50/70">
          {content}
        </Link>
      ) : (
        content
      )}
    </li>
  )
}

function severityHint(severity: SeverityBreakdown): string {
  const parts = (['critical', 'high', 'medium'] as const)
    .filter((key) => severity[key] > 0)
    .map((key) => `${severity[key]} ${humanise(key).toLowerCase()}`)
  return parts.length ? parts.join(' · ') : 'No high-severity risks'
}
