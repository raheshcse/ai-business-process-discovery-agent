import { Link } from 'react-router-dom'
import { PageShell } from '@/components/layout/PageShell'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Chip } from '@/components/ui/StatusChip'
import { ErrorState, LoadingState } from '@/components/ui/States'
import { ShieldIcon } from '@/components/ui/icons'
import { useGovernanceCatalogue } from '@/hooks/queries'
import { humanise } from '@/lib/format'
import type { GovernanceConstruct } from '@/types/api'

/**
 * The rulebook, independent of any single run.
 *
 * Someone deciding whether to trust this system needs to see the rules
 * before they see a result, and needs to see rules that never fired as
 * well as ones that did.
 */
export function GovernanceOverviewPage() {
  const { data, isLoading, isError, error, refetch } = useGovernanceCatalogue()

  return (
    <PageShell
      title="Governance"
      description="The rules every analysis in this system must satisfy"
    >
      {isLoading ? <LoadingState label="Loading the governance rulebook…" /> : null}
      {isError ? <ErrorState error={error} onRetry={() => void refetch()} /> : null}

      {data ? (
        <>
          <Card className="border-navy-800 bg-hero-gradient text-white">
            <CardBody>
              <div className="flex flex-wrap items-start gap-4">
                <div className="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-accent-500/15 text-accent-400 ring-1 ring-inset ring-accent-400/30">
                  <ShieldIcon />
                </div>
                <div className="min-w-0 flex-1">
                  <h2 className="text-base font-semibold">
                    Analyses are gated, not just generated
                  </h2>
                  <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-navy-200">
                    Each of the five analysis stages is preceded by a readiness gate
                    and followed by a validation rule. A stage only runs if its
                    evidence requirements are met, and its output is only passed on
                    if it survives validation. Any failure stops the workflow at a
                    named terminal state instead of producing an unsupported answer.
                    Every decision is written to a tamper-evident log.
                  </p>
                  <p className="mt-3 max-w-3xl text-sm leading-relaxed text-navy-300">
                    This governs the <em>process</em>. It does not and cannot
                    guarantee that the model's reading of your documents is correct.
                  </p>
                </div>
              </div>
            </CardBody>
          </Card>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Threshold
              label="Readiness threshold"
              value={data.gamma_threshold.toFixed(2)}
              hint="A stage must score above this to be allowed to run."
            />
            <Threshold
              label="Minimum evidence relevance"
              value={data.minimum_evidence_score.toFixed(2)}
              hint="Retrieved passages scoring below this do not count as evidence."
            />
            <Threshold
              label="Minimum process findings"
              value={String(data.minimum_process_findings)}
              hint="Required before later stages may build on the process analysis."
            />
          </div>

          <ConstructList
            title="Readiness gates"
            description="Run before a stage. They ask whether there is enough grounded evidence to proceed at all."
            constructs={data.pre_nodes}
          />
          <ConstructList
            title="Validation rules"
            description="Run after a stage, on what it produced. They ask whether the output is grounded and in scope."
            constructs={data.invariants}
          />
          <ConstructList
            title="Stopping states"
            description="Where the workflow lands when a check fails. Each one is deliberate, and none of them produce a conclusion."
            constructs={data.terminal_states}
          />

          <Card>
            <CardBody>
              <p className="text-sm text-navy-600">
                To see these rules applied to a specific analysis, open a project and
                choose a run.{' '}
                <Link
                  to="/projects"
                  className="font-medium text-accent-600 hover:text-accent-500"
                >
                  Browse projects
                </Link>
                .
              </p>
            </CardBody>
          </Card>
        </>
      ) : null}
    </PageShell>
  )
}

function Threshold({
  label,
  value,
  hint,
}: {
  label: string
  value: string
  hint: string
}) {
  return (
    <div className="card p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-navy-500">
        {label}
      </p>
      <p className="mt-2 text-3xl font-semibold tabular-nums text-navy-900">{value}</p>
      <p className="mt-1 text-xs leading-relaxed text-navy-500">{hint}</p>
    </div>
  )
}

function ConstructList({
  title,
  description,
  constructs,
}: {
  title: string
  description: string
  constructs: GovernanceConstruct[]
}) {
  return (
    <Card>
      <CardHeader title={title} description={description} />
      <CardBody className="p-0 sm:p-0">
        <ul className="divide-y divide-navy-100">
          {constructs.map((construct) => (
            <li key={construct.name} className="px-5 py-4 sm:px-6">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-navy-900">
                    {humanise(construct.name)}
                  </p>
                  <p className="mt-1 text-sm leading-relaxed text-navy-600">
                    {construct.description}
                  </p>
                  <p className="mt-1.5 font-mono text-[11px] text-navy-400">
                    {construct.name}
                  </p>
                </div>
                {construct.on_violation ? (
                  <Chip tone="warning">Stops at {construct.on_violation}</Chip>
                ) : (
                  <Chip tone="neutral">{humanise(construct.stage)}</Chip>
                )}
              </div>
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  )
}
