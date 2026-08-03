import { Link, useParams } from 'react-router-dom'
import { PageShell } from '@/components/layout/PageShell'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Chip, WorkflowStatusChip } from '@/components/ui/StatusChip'
import { Table, Td, Th } from '@/components/ui/Table'
import {
  EmptyState,
  ErrorState,
  LoadingState,
  SkeletonRows,
} from '@/components/ui/States'
import { ArrowLeftIcon, ChevronRightIcon, SparkIcon } from '@/components/ui/icons'
import { DocumentTable } from '@/features/documents/DocumentTable'
import { UploadArea } from '@/features/documents/UploadArea'
import { StartAnalysisPanel } from '@/features/analysis/StartAnalysisPanel'
import { useAnalyses, useDocuments, useProject } from '@/hooks/queries'
import { formatDateTime, formatRelative, humanise } from '@/lib/format'

export function ProjectWorkspacePage() {
  const { projectId } = useParams<{ projectId: string }>()
  const project = useProject(projectId)
  const documents = useDocuments(projectId)
  const analyses = useAnalyses(projectId)

  if (project.isLoading) {
    return (
      <PageShell title="Loading project…">
        <LoadingState />
      </PageShell>
    )
  }

  if (project.isError || !project.data) {
    return (
      <PageShell title="Project">
        <ErrorState
          error={project.error}
          onRetry={() => void project.refetch()}
          title="We could not open this project"
        />
        <Link
          to="/projects"
          className="inline-flex items-center gap-2 text-sm font-medium text-accent-600 hover:text-accent-500"
        >
          <ArrowLeftIcon className="h-4 w-4" />
          Back to all projects
        </Link>
      </PageShell>
    )
  }

  const documentList = documents.data ?? []
  const indexedCount = documentList.filter(
    (document) => document.index_status === 'indexed',
  ).length

  return (
    <PageShell
      title={project.data.name}
      description={project.data.objective}
      actions={
        <Chip tone={project.data.status === 'active' ? 'info' : 'neutral'}>
          {humanise(project.data.status)}
        </Chip>
      }
    >
      <Link
        to="/projects"
        className="inline-flex items-center gap-2 text-sm font-medium text-navy-500 hover:text-navy-800"
      >
        <ArrowLeftIcon className="h-4 w-4" />
        All projects
      </Link>

      {/* Summary */}
      <Card>
        <CardHeader title="Project summary" />
        <CardBody>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3 lg:grid-cols-5">
            <Detail label="Client" value={project.data.client_name ?? '—'} />
            <Detail label="Department" value={project.data.department ?? '—'} />
            <Detail label="Industry" value={project.data.industry ?? '—'} />
            <Detail
              label="Evidence"
              value={`${indexedCount} of ${documentList.length} ready`}
            />
            <Detail label="Created" value={formatDateTime(project.data.created_at)} />
          </dl>
        </CardBody>
      </Card>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
        {/* Documents */}
        <Card className="xl:col-span-3">
          <CardHeader
            title="Documents"
            description="Uploaded files are text-extracted and indexed automatically"
          />
          <CardBody className="p-0 sm:p-0">
            {documents.isLoading ? (
              <div className="p-5 sm:p-6">
                <SkeletonRows rows={3} />
              </div>
            ) : documents.isError ? (
              <div className="p-5 sm:p-6">
                <ErrorState
                  error={documents.error}
                  onRetry={() => void documents.refetch()}
                />
              </div>
            ) : (
              <DocumentTable projectId={project.data.id} documents={documentList} />
            )}
          </CardBody>
        </Card>

        {/* Upload */}
        <Card className="xl:col-span-2">
          <CardHeader title="Add evidence" />
          <CardBody>
            <UploadArea projectId={project.data.id} />
          </CardBody>
        </Card>
      </div>

      {/* Start analysis */}
      <Card>
        <CardHeader
          title="Run a business process analysis"
          description="Five governed stages: process discovery, bottlenecks, risks, automation, and an executive summary"
        />
        <CardBody>
          <StartAnalysisPanel projectId={project.data.id} documents={documentList} />
        </CardBody>
      </Card>

      {/* Past analyses */}
      <Card>
        <CardHeader
          title="Analyses"
          description={`${analyses.data?.length ?? 0} run${analyses.data?.length === 1 ? '' : 's'} in this project`}
        />
        <CardBody className="p-0 sm:p-0">
          {analyses.isLoading ? (
            <div className="p-5 sm:p-6">
              <SkeletonRows rows={2} />
            </div>
          ) : analyses.isError ? (
            <div className="p-5 sm:p-6">
              <ErrorState
                error={analyses.error}
                onRetry={() => void analyses.refetch()}
              />
            </div>
          ) : (analyses.data?.length ?? 0) === 0 ? (
            <div className="p-5 sm:p-6">
              <EmptyState
                icon={<SparkIcon className="h-10 w-10" />}
                title="No analyses yet"
                description="Once you run an analysis it appears here with its status, results and full governance record."
              />
            </div>
          ) : (
            <Table
              head={
                <tr>
                  <Th>Question</Th>
                  <Th>Status</Th>
                  <Th className="hidden md:table-cell">Evidence</Th>
                  <Th className="hidden sm:table-cell">Started</Th>
                  <Th />
                </tr>
              }
            >
              {analyses.data?.map((run) => (
                <tr key={run.id} className="hover:bg-navy-50/60">
                  <Td>
                    <Link
                      to={`/analyses/${run.id}`}
                      className="font-medium text-navy-900 hover:text-accent-600"
                    >
                      {run.question}
                    </Link>
                    {run.terminal_state_name ? (
                      <p className="mt-0.5 text-xs text-amber-700">
                        Terminal state: {humanise(run.terminal_state_name)}
                      </p>
                    ) : null}
                  </Td>
                  <Td>
                    <WorkflowStatusChip status={run.status} />
                  </Td>
                  <Td className="hidden text-navy-600 md:table-cell">
                    {run.source_count} source{run.source_count === 1 ? '' : 's'}
                  </Td>
                  <Td className="hidden whitespace-nowrap text-navy-500 sm:table-cell">
                    {formatRelative(run.created_at)}
                  </Td>
                  <Td className="text-right">
                    <Link
                      to={`/analyses/${run.id}`}
                      className="inline-flex items-center gap-1 text-sm font-medium text-accent-600 hover:text-accent-500"
                    >
                      Open
                      <ChevronRightIcon className="h-4 w-4" />
                    </Link>
                  </Td>
                </tr>
              ))}
            </Table>
          )}
        </CardBody>
      </Card>
    </PageShell>
  )
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-navy-500">
        {label}
      </dt>
      <dd className="mt-1 text-sm font-medium text-navy-900">{value}</dd>
    </div>
  )
}
