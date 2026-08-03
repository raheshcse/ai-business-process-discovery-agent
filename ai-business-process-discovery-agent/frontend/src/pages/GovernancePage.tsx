import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { PageShell } from '@/components/layout/PageShell'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Chip, OutcomeChip } from '@/components/ui/StatusChip'
import { Table, Td, Th } from '@/components/ui/Table'
import { Banner, ErrorState, LoadingState } from '@/components/ui/States'
import {
  AlertIcon,
  ArrowLeftIcon,
  CheckIcon,
  CrossIcon,
  ShieldIcon,
} from '@/components/ui/icons'
import { useGovernanceReport } from '@/hooks/queries'
import { humanise, truncateHash } from '@/lib/format'
import type { GovernanceReport, LedgerAuditCheck } from '@/types/api'

/**
 * Written for a business reader first.
 *
 * The underlying vocabulary is PreNodes, invariants, Gamma thresholds and
 * hash chains. None of that means anything to the person who has to decide
 * whether to trust the analysis, so each construct is explained in terms of
 * what it protects them from, with the technical name kept alongside rather
 * than instead.
 */
export function GovernancePage() {
  const { runId } = useParams<{ runId: string }>()
  const { data, isLoading, isError, error, refetch } = useGovernanceReport(runId)
  const [showTechnical, setShowTechnical] = useState(false)

  if (isLoading) {
    return (
      <PageShell title="Governance &amp; audit">
        <LoadingState label="Loading the audit trail…" />
      </PageShell>
    )
  }

  if (isError || !data) {
    return (
      <PageShell title="Governance &amp; audit">
        <ErrorState
          error={error}
          onRetry={() => void refetch()}
          title="We could not load the audit trail"
        />
      </PageShell>
    )
  }

  return (
    <PageShell
      title="Governance &amp; audit"
      description={data.question}
      actions={
        <Button
          variant="secondary"
          size="sm"
          onClick={() => setShowTechnical((value) => !value)}
        >
          {showTechnical ? 'Hide' : 'Show'} technical detail
        </Button>
      }
    >
      <Link
        to={`/analyses/${data.analysis_run_id}`}
        className="inline-flex items-center gap-2 text-sm font-medium text-navy-500 hover:text-navy-800"
      >
        <ArrowLeftIcon className="h-4 w-4" />
        Back to results
      </Link>

      <Verdict report={data} />
      <DecisionTrail report={data} showTechnical={showTechnical} />
      <AuditChecks checks={data.audit_checks} />
      <ChainIntegrity report={data} />
      {showTechnical ? <LedgerTable report={data} /> : null}
    </PageShell>
  )
}

function Verdict({ report }: { report: GovernanceReport }) {
  const allowed = report.governance_status === 'allowed'
  const needsReview = report.human_review_required
  const denied = report.decisions.filter((d) => d.outcome === 'denied')

  return (
    <Card
      className={
        allowed
          ? 'border-emerald-200'
          : needsReview
            ? 'border-amber-300'
            : 'border-amber-300'
      }
    >
      <CardBody className="flex flex-wrap items-start gap-4">
        <div
          className={`grid h-11 w-11 shrink-0 place-items-center rounded-lg ${
            allowed ? 'bg-emerald-50 text-emerald-600' : 'bg-amber-50 text-amber-600'
          }`}
        >
          {allowed ? <ShieldIcon /> : <AlertIcon />}
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-base font-semibold text-navy-900">
            {allowed
              ? 'This analysis passed every governance check'
              : needsReview
                ? 'This analysis is waiting on human judgement'
                : 'This analysis was stopped by a governance check'}
          </h2>
          <p className="mt-1.5 text-sm leading-relaxed text-navy-600">
            {allowed
              ? `All ${report.decisions.length} checks allowed the workflow to continue. Every stage was permitted to run only after its evidence requirements were met, and every result was validated before the next stage used it.`
              : denied.length > 0
                ? `The workflow stopped at ${humanise(denied[0].construct_name)}. It produced no final conclusion rather than one it could not support.`
                : 'The workflow stopped before completing. Details are below.'}
          </p>

          <div className="mt-3 flex flex-wrap gap-2">
            <Chip tone={allowed ? 'success' : 'warning'}>
              {humanise(report.governance_status)}
            </Chip>
            <Chip tone="neutral">Stage: {humanise(report.governance_stage)}</Chip>
            {report.terminal_state_name ? (
              <Chip tone="warning">
                Stopped at {humanise(report.terminal_state_name)}
              </Chip>
            ) : null}
          </div>

          {report.denial_summary ? (
            <div className="mt-4">
              <Banner tone="warning" title="Why it stopped">
                <p>{String(report.denial_summary.safe_reason ?? '')}</p>
                {report.human_review_required ? (
                  <p className="mt-2">
                    A person with the right authority needs to review this before the
                    analysis can go further. This application has no approval workflow
                    yet, so that review happens outside the system.
                  </p>
                ) : null}
              </Banner>
            </div>
          ) : null}

          {report.errors.length > 0 ? (
            <ul className="mt-3 list-disc space-y-1 pl-5">
              {report.errors.map((message, index) => (
                <li key={index} className="text-sm text-red-700">
                  {message}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </CardBody>
    </Card>
  )
}

/** Plain-language names for the eleven gates. */
const CONSTRUCT_COPY: Record<string, string> = {
  process_discovery_pre_node:
    'Checked there was relevant evidence from this project before reading the process.',
  bottleneck_analysis_pre_node:
    'Checked the process findings were evidence-backed before looking for bottlenecks.',
  risk_analysis_pre_node:
    'Checked usable evidence existed before assessing risk.',
  automation_analysis_pre_node:
    'Checked both process and bottleneck evidence existed before proposing automation.',
  final_synthesis_pre_node:
    'Checked every earlier stage had passed its validation before writing the summary.',
  evidence_reference_invariant:
    'Confirmed every process finding cited a real source from your documents.',
  process_analysis_invariant:
    'Confirmed the process findings actually described process elements.',
  bottleneck_analysis_invariant:
    'Confirmed each bottleneck was supported by a cited source.',
  risk_scope_invariant:
    'Confirmed the risk findings stayed operational and drew no legal or compliance conclusions.',
  automation_safety_invariant:
    'Confirmed high-impact automation proposals kept a human in the loop.',
  final_analysis_invariant:
    'Confirmed the summary stayed grounded and declared its assumptions and gaps.',
  INSUFFICIENT_EVIDENCE:
    'Stopped because the retrieved evidence could not support any grounded analysis.',
}

function DecisionTrail({
  report,
  showTechnical,
}: {
  report: GovernanceReport
  showTechnical: boolean
}) {
  return (
    <Card>
      <CardHeader
        title="What was checked, and when"
        description="In the order the workflow ran them. A blocked check stops the analysis immediately."
      />
      <CardBody className="p-0 sm:p-0">
        {report.decisions.length === 0 ? (
          <div className="px-5 py-8 sm:px-6">
            <p className="text-sm text-navy-500">
              No governance decisions were recorded. The workflow stopped before
              reaching its first gate.
            </p>
          </div>
        ) : (
          <ol className="divide-y divide-navy-100">
            {report.decisions.map((decision) => (
              <li key={decision.decision_id} className="flex gap-4 px-5 py-4 sm:px-6">
                <span
                  className={`mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full ${
                    decision.outcome === 'allowed'
                      ? 'bg-emerald-50 text-emerald-600'
                      : 'bg-red-50 text-red-600'
                  }`}
                >
                  {decision.outcome === 'allowed' ? (
                    <CheckIcon className="h-4 w-4" />
                  ) : (
                    <CrossIcon className="h-4 w-4" />
                  )}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-medium text-navy-900">
                      {CONSTRUCT_COPY[decision.construct_name] ??
                        humanise(decision.construct_name)}
                    </p>
                    <OutcomeChip outcome={decision.outcome} />
                  </div>
                  <p className="mt-1 text-xs text-navy-500">
                    {decision.construct_type === 'pre_node'
                      ? 'Ran before the stage'
                      : decision.construct_type === 'invariant'
                        ? 'Ran after the stage, on its output'
                        : humanise(decision.construct_type)}{' '}
                    · {decision.source_count} evidence source
                    {decision.source_count === 1 ? '' : 's'}
                    {decision.terminal_state_name
                      ? ` · stopped at ${decision.terminal_state_name}`
                      : ''}
                  </p>
                  {showTechnical ? (
                    <p className="mt-1 font-mono text-[11px] text-navy-400">
                      {decision.construct_name} · node {decision.node_name} ·{' '}
                      {decision.recorded_at}
                    </p>
                  ) : null}
                </div>
              </li>
            ))}
          </ol>
        )}
      </CardBody>
    </Card>
  )
}

function AuditChecks({ checks }: { checks: LedgerAuditCheck[] }) {
  if (checks.length === 0) return null
  const failed = checks.filter((check) => !check.passed)

  return (
    <Card>
      <CardHeader
        title="Independent audit of the record"
        description="Five structural checks over the audit log itself, asking whether governance was properly recorded — not whether the analysis is correct."
      />
      <CardBody className="space-y-3">
        {failed.length > 0 ? (
          <Banner tone="warning" title={`${failed.length} of 5 checks are not met`}>
            These are reported exactly as the ledger reports them. Two of the five
            require an approval workflow this application does not have yet, so they
            are expected to fail whenever a run stops at a terminal state.
          </Banner>
        ) : null}

        <ul className="space-y-2.5">
          {checks.map((check) => (
            <li
              key={check.name}
              className={`flex gap-3 rounded-lg border px-4 py-3 ${
                check.passed
                  ? 'border-emerald-200 bg-emerald-50/50'
                  : 'border-amber-200 bg-amber-50/60'
              }`}
            >
              <span
                className={`mt-0.5 shrink-0 ${
                  check.passed ? 'text-emerald-600' : 'text-amber-600'
                }`}
              >
                {check.passed ? (
                  <CheckIcon className="h-5 w-5" />
                ) : (
                  <AlertIcon className="h-5 w-5" />
                )}
              </span>
              <div className="min-w-0">
                <p className="text-sm font-medium text-navy-900">{check.label}</p>
                <p className="mt-0.5 text-sm leading-relaxed text-navy-600">
                  {check.explanation}
                </p>
                {check.violation_count > 0 ? (
                  <p className="mt-1 text-xs font-medium text-amber-800">
                    {check.violation_count} record
                    {check.violation_count === 1 ? '' : 's'} affected
                  </p>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  )
}

function ChainIntegrity({ report }: { report: GovernanceReport }) {
  return (
    <Card>
      <CardHeader
        title="Tamper evidence"
        description="Every governance event is written to an append-only log where each entry is cryptographically linked to the one before it."
      />
      <CardBody className="space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-navy-500">
              Record integrity
            </p>
            <p className="mt-1.5">
              <Chip tone={report.chain_verified ? 'success' : 'danger'}>
                {report.chain_verified ? 'Unaltered' : 'Verification failed'}
              </Chip>
            </p>
            <p className="mt-1.5 text-xs leading-relaxed text-navy-500">
              {report.chain_verified
                ? 'Recomputing every hash reproduces the stored chain, so no entry has been edited or removed.'
                : 'The stored chain does not match its own hashes. Treat this record as unreliable.'}
            </p>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-navy-500">
              Events in this run
            </p>
            <p className="mt-1.5 text-2xl font-semibold tabular-nums text-navy-900">
              {report.ledger_entries.length}
            </p>
            <p className="mt-1 text-xs text-navy-500">
              Log position {report.checkpoint_sequence ?? '—'}
            </p>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-navy-500">
              Latest checkpoint
            </p>
            <p className="mt-1.5 break-all font-mono text-xs text-navy-700">
              {truncateHash(report.checkpoint_hash, 24)}
            </p>
            <p className="mt-1 text-xs leading-relaxed text-navy-500">
              Record this value externally to detect the log being replaced
              wholesale later.
            </p>
          </div>
        </div>

        <div className="rounded-lg border border-navy-200 bg-navy-50/60 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-navy-600">
            What this does and does not prove
          </p>
          <p className="mt-1.5 text-sm leading-relaxed text-navy-600">
            {report.certificate_note ??
              'This certifies the governance process, not the underlying system, model, or business domain.'}
          </p>
        </div>
      </CardBody>
    </Card>
  )
}

function LedgerTable({ report }: { report: GovernanceReport }) {
  return (
    <Card>
      <CardHeader
        title="Audit ledger"
        description="Raw hash-chained entries for this run"
      />
      <CardBody className="p-0 sm:p-0">
        <Table
          head={
            <tr>
              <Th>#</Th>
              <Th>Type</Th>
              <Th>Details</Th>
              <Th className="hidden lg:table-cell">Previous hash</Th>
              <Th className="hidden lg:table-cell">Entry hash</Th>
            </tr>
          }
        >
          {report.ledger_entries.map((entry) => (
            <tr key={entry.entry_id}>
              <Td className="tabular-nums text-navy-500">{entry.sequence}</Td>
              <Td>
                <Chip tone="neutral">{entry.entry_type}</Chip>
              </Td>
              <Td className="font-mono text-[11px] text-navy-600">
                {Object.entries(entry.payload)
                  .map(([key, value]) => `${key}=${String(value)}`)
                  .join(' · ')}
              </Td>
              <Td className="hidden font-mono text-[11px] text-navy-400 lg:table-cell">
                {truncateHash(entry.prev_hash, 10)}
              </Td>
              <Td className="hidden font-mono text-[11px] text-navy-600 lg:table-cell">
                {truncateHash(entry.entry_hash, 10)}
              </Td>
            </tr>
          ))}
        </Table>
      </CardBody>
    </Card>
  )
}
