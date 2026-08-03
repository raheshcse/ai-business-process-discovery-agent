import { Link, useParams } from 'react-router-dom'
import { PageShell } from '@/components/layout/PageShell'
import { Card, CardBody, CardHeader, StatCard } from '@/components/ui/Card'
import { Chip, WorkflowStatusChip } from '@/components/ui/StatusChip'
import { Table, Td, Th } from '@/components/ui/Table'
import {
  Banner,
  EmptyState,
  ErrorState,
  LoadingState,
} from '@/components/ui/States'
import {
  AlertIcon,
  ArrowLeftIcon,
  BoltIcon,
  ClockIcon,
  DocumentIcon,
  ShieldIcon,
  SparkIcon,
} from '@/components/ui/icons'
import { AnalysisSection, Caveats } from '@/features/analysis/AnalysisSection'
import { ProcessFlow } from '@/features/analysis/ProcessFlow'
import { RunProgress } from '@/features/analysis/RunProgress'
import { isRunInProgress, useAnalysis } from '@/hooks/queries'
import { formatDuration, formatDateTime, humanise } from '@/lib/format'
import type { AnalysisRunDetail } from '@/types/api'

export function AnalysisResultsPage() {
  const { runId } = useParams<{ runId: string }>()
  const { data, isLoading, isError, error, refetch } = useAnalysis(runId)

  if (isLoading) {
    return (
      <PageShell title="Analysis">
        <LoadingState label="Loading analysis…" />
      </PageShell>
    )
  }

  if (isError || !data) {
    return (
      <PageShell title="Analysis">
        <ErrorState
          error={error}
          onRetry={() => void refetch()}
          title="We could not load this analysis"
        />
      </PageShell>
    )
  }

  return (
    <PageShell
      title="Analysis results"
      description={data.question}
      actions={<WorkflowStatusChip status={data.status} />}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          to={`/projects/${data.project_id}`}
          className="inline-flex items-center gap-2 text-sm font-medium text-navy-500 hover:text-navy-800"
        >
          <ArrowLeftIcon className="h-4 w-4" />
          Back to project
        </Link>
        <Link
          to={`/analyses/${data.id}/governance`}
          className="inline-flex items-center gap-2 rounded-lg border border-navy-200 bg-white px-3 py-1.5 text-sm font-medium text-navy-700 hover:bg-navy-50"
        >
          <ShieldIcon className="h-4 w-4" />
          Governance &amp; audit
        </Link>
      </div>

      {isRunInProgress(data.status) ? <InProgress run={data} /> : null}
      {!isRunInProgress(data.status) && data.status !== 'completed' ? (
        <StoppedNotice run={data} />
      ) : null}

      {data.status === 'completed' ? <Results run={data} /> : null}
    </PageShell>
  )
}

function InProgress({ run }: { run: AnalysisRunDetail }) {
  return (
    <Card>
      <CardHeader
        title="Analysis in progress"
        description="Each stage runs through a governance gate before it starts and an evidence check after it finishes. This page updates itself."
      />
      <CardBody className="space-y-4">
        <RunProgress status={run.status} currentStage={run.current_stage} />
        <p className="text-sm text-navy-500">
          Started {formatDateTime(run.started_at ?? run.created_at)}. Five sequential
          model calls typically take a few minutes.
        </p>
      </CardBody>
    </Card>
  )
}

/** Blocked, insufficient-evidence and failed runs each need a different
 *  explanation, and none of them should look like a bug to a business user. */
function StoppedNotice({ run }: { run: AnalysisRunDetail }) {
  const copy: Record<string, { title: string; body: string; tone: 'warning' | 'danger' }> =
    {
      insufficient_evidence: {
        title: 'Your documents did not cover this question',
        body: 'The search found no passages relevant enough to support an answer. This is not a failure — the workflow refuses to answer from anything other than your evidence. Try uploading more documentation, or asking a narrower question.',
        tone: 'warning',
      },
      governance_blocked: {
        title: 'A governance gate stopped this analysis',
        body: 'One of the checks that runs before or after each stage was not satisfied, so the workflow stopped rather than produce a conclusion it could not support. The governance page shows exactly which check and why.',
        tone: 'warning',
      },
      human_review_required: {
        title: 'This analysis needs a person to review it',
        body: 'A safety check determined that the automation proposals here require human judgement before going further. The workflow stopped deliberately and is waiting on you.',
        tone: 'warning',
      },
      failed: {
        title: 'The analysis could not finish',
        body: 'Something went wrong while running the workflow. The details below are the only information the system recorded.',
        tone: 'danger',
      },
    }

  const notice = copy[run.status] ?? {
    title: 'This analysis did not complete',
    body: 'The workflow stopped before producing a final summary.',
    tone: 'warning' as const,
  }

  return (
    <>
      <Banner
        tone={notice.tone}
        title={notice.title}
        action={
          <Link
            to={`/analyses/${run.id}/governance`}
            className="shrink-0 whitespace-nowrap text-sm font-semibold underline underline-offset-2"
          >
            See why
          </Link>
        }
      >
        <p>{notice.body}</p>
        {run.terminal_state_name ? (
          <p className="mt-2">
            <span className="font-medium">Terminal state:</span>{' '}
            <code className="rounded bg-black/5 px-1">{run.terminal_state_name}</code>
          </p>
        ) : null}
        {run.errors.length > 0 ? (
          <ul className="mt-2 list-disc space-y-1 pl-4">
            {run.errors.map((message, index) => (
              <li key={index}>{message}</li>
            ))}
          </ul>
        ) : null}
      </Banner>

      {/* Partial results are still useful, so show whatever completed. */}
      <PartialResults run={run} />
    </>
  )
}

function PartialResults({ run }: { run: AnalysisRunDetail }) {
  const stages = [
    { key: 'process_analysis', label: 'Process discovery' },
    { key: 'bottleneck_analysis', label: 'Bottlenecks' },
    { key: 'risk_analysis', label: 'Risks and controls' },
    { key: 'automation_analysis', label: 'Automation' },
  ] as const

  const completed = stages.filter((stage) => run[stage.key] !== null)
  if (completed.length === 0) return null

  return (
    <Card>
      <CardHeader
        title="Partial results"
        description="Stages that finished before the workflow stopped. Treat these as provisional — they were never validated by the final synthesis."
      />
      <CardBody className="space-y-6">
        {completed.map((stage) => {
          const analysis = run[stage.key]!
          return (
            <div key={stage.key}>
              <h3 className="text-sm font-semibold text-navy-900">{stage.label}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-navy-700">
                {analysis.summary}
              </p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {analysis.findings.map((finding, index) => (
                  <li key={index} className="text-sm text-navy-600">
                    <span className="font-medium text-navy-800">{finding.title}</span> —{' '}
                    {finding.description}
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </CardBody>
    </Card>
  )
}

function Results({ run }: { run: AnalysisRunDetail }) {
  const riskFindings = run.risk_analysis?.findings ?? []
  const automationFindings = run.automation_analysis?.findings ?? []
  const bottleneckFindings = run.bottleneck_analysis?.findings ?? []
  const seriousRisks = riskFindings.filter(
    (finding) => finding.severity === 'critical' || finding.severity === 'high',
  ).length

  return (
    <>
      {/* Executive summary first: it is what most readers want. */}
      {run.final_analysis ? (
        <Card className="border-navy-800 bg-hero-gradient text-white">
          <div className="border-b border-white/10 px-5 py-4 sm:px-6">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="flex items-center gap-2 text-sm font-semibold">
                <SparkIcon className="h-4 w-4 text-accent-400" />
                Executive summary
              </h2>
              <span className="text-xs text-navy-300">
                {run.final_analysis.provider_name ?? 'model'} ·{' '}
                {run.final_analysis.model_name ?? 'unknown'}
              </span>
            </div>
          </div>
          <div className="px-5 py-5 sm:px-6">
            <p className="text-[15px] leading-relaxed text-navy-100">
              {run.final_analysis.summary}
            </p>
            {run.final_analysis.findings.length > 0 ? (
              <ul className="mt-4 space-y-2.5">
                {run.final_analysis.findings.map((finding, index) => (
                  <li key={index} className="flex gap-3">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent-400" />
                    <div>
                      <p className="text-sm font-medium text-white">{finding.title}</p>
                      <p className="mt-0.5 text-sm leading-relaxed text-navy-200">
                        {finding.recommendation}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </Card>
      ) : null}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Process steps found"
          value={run.process_analysis?.findings.length ?? 0}
        />
        <StatCard label="Bottlenecks" value={bottleneckFindings.length} tone="warning" />
        <StatCard
          label="Risks"
          value={riskFindings.length}
          hint={seriousRisks > 0 ? `${seriousRisks} high or critical` : 'None severe'}
          tone={seriousRisks > 0 ? 'danger' : 'default'}
        />
        <StatCard
          label="Automation opportunities"
          value={automationFindings.length}
          tone="success"
        />
      </div>

      {/* Process walkthrough */}
      <Card>
        <CardHeader
          title="Business process"
          description="The process as your documents describe it, in the order it was discovered"
        />
        <CardBody>
          {run.process_analysis ? (
            <>
              <p className="mb-5 text-sm leading-relaxed text-navy-700">
                {run.process_analysis.summary}
              </p>
              <ProcessFlow
                findings={run.process_analysis.findings}
                citations={run.citations}
              />
              <div className="mt-5">
                <Caveats analysis={run.process_analysis} />
              </div>
            </>
          ) : (
            <EmptyState
              icon={<SparkIcon className="h-10 w-10" />}
              title="No process discovered"
              description="This stage did not produce a result."
            />
          )}
        </CardBody>
      </Card>

      <AnalysisSection
        title="Bottlenecks"
        description="Where the process waits, repeats or doubles back"
        analysis={run.bottleneck_analysis}
        citations={run.citations}
        order="severity"
        icon={<ClockIcon className="h-10 w-10" />}
        emptyTitle="No bottleneck analysis"
        emptyDescription="This stage did not run or produced no result."
      />

      <AnalysisSection
        title="Risks and controls"
        description="Operational and control concerns. The workflow deliberately does not draw legal or regulatory conclusions."
        analysis={run.risk_analysis}
        citations={run.citations}
        order="severity"
        icon={<AlertIcon className="h-10 w-10" />}
        emptyTitle="No risk analysis"
        emptyDescription="This stage did not run or produced no result."
      />

      <AnalysisSection
        title="Automation opportunities"
        description="Ranked by severity, which here reflects impact and the degree of human oversight required"
        analysis={run.automation_analysis}
        citations={run.citations}
        order="severity"
        icon={<BoltIcon className="h-10 w-10" />}
        emptyTitle="No automation analysis"
        emptyDescription="This stage did not run or produced no result."
      />

      {/* Evidence */}
      <Card>
        <CardHeader
          title="Source documents"
          description={`${run.citations.length} passage${run.citations.length === 1 ? '' : 's'} retrieved from your documents and shown to the model`}
          action={
            <span className="text-xs text-navy-500">
              {run.retrieval_provider ?? '—'} · {run.retrieval_model ?? '—'}
            </span>
          }
        />
        <CardBody className="p-0 sm:p-0">
          {run.citations.length === 0 ? (
            <div className="p-5 sm:p-6">
              <EmptyState
                icon={<DocumentIcon className="h-10 w-10" />}
                title="No sources recorded"
                description="This analysis has no retrieved evidence attached."
              />
            </div>
          ) : (
            <Table
              head={
                <tr>
                  <Th>Source</Th>
                  <Th>Document</Th>
                  <Th className="hidden sm:table-cell">Section</Th>
                  <Th className="text-right">Relevance</Th>
                </tr>
              }
            >
              {run.citations.map((citation) => (
                <tr key={citation.chunk_id}>
                  <Td>
                    <Chip tone="info">{citation.source_id}</Chip>
                  </Td>
                  <Td className="font-medium text-navy-900">
                    {citation.filename ?? citation.document_id}
                  </Td>
                  <Td className="hidden text-navy-600 sm:table-cell">
                    Section {citation.chunk_index + 1}
                  </Td>
                  <Td className="text-right tabular-nums text-navy-700">
                    {citation.score.toFixed(3)}
                  </Td>
                </tr>
              ))}
            </Table>
          )}
          {run.context_truncated ? (
            <div className="px-5 pb-5 sm:px-6">
              <Banner tone="warning" title="Evidence was truncated">
                More relevant passages were found than fit in the model's context
                window. Narrow your question or limit the analysis to specific
                documents for fuller coverage.
              </Banner>
            </div>
          ) : null}
        </CardBody>
      </Card>

      {/* Run metadata */}
      <Card>
        <CardHeader title="Run details" />
        <CardBody>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
            <Meta label="Started" value={formatDateTime(run.started_at)} />
            <Meta
              label="Duration"
              value={formatDuration(run.started_at, run.completed_at)}
            />
            <Meta label="Governance" value={humanise(run.governance_status)} />
            <Meta
              label="Passages searched"
              value={`${run.retrieved_count} retrieved, top ${run.top_k}`}
            />
          </dl>
        </CardBody>
      </Card>
    </>
  )
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-navy-500">
        {label}
      </dt>
      <dd className="mt-1 text-sm font-medium text-navy-900">{value}</dd>
    </div>
  )
}
