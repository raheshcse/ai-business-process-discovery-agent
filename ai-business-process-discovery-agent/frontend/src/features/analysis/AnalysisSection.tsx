import type { ReactNode } from 'react'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/States'
import { formatPercent } from '@/lib/format'
import type { BusinessAnalysisResult, Citation } from '@/types/api'
import { FindingCard } from './FindingCard'

export function AnalysisSection({
  title,
  description,
  analysis,
  citations,
  emptyTitle,
  emptyDescription,
  icon,
  order = 'default',
}: {
  title: string
  description: string
  analysis: BusinessAnalysisResult | null
  citations: Citation[]
  emptyTitle: string
  emptyDescription: string
  icon?: ReactNode
  /** `severity` sorts most serious first, which is what a reader wants
   *  for risks but not for ordered process steps. */
  order?: 'default' | 'severity'
}) {
  if (!analysis) {
    return (
      <Card>
        <CardHeader title={title} description={description} />
        <CardBody>
          <EmptyState icon={icon} title={emptyTitle} description={emptyDescription} />
        </CardBody>
      </Card>
    )
  }

  const RANK = { critical: 0, high: 1, medium: 2, low: 3, informational: 4 }
  const findings =
    order === 'severity'
      ? [...analysis.findings].sort(
          (a, b) => RANK[a.severity] - RANK[b.severity],
        )
      : analysis.findings

  return (
    <Card>
      <CardHeader
        title={title}
        description={description}
        action={
          <span
            className="shrink-0 text-xs text-navy-500"
            title="The model's own confidence in this analysis. It is not a measure of correctness."
          >
            Model confidence {formatPercent(analysis.confidence)}
          </span>
        }
      />
      <CardBody className="space-y-4">
        <p className="text-sm leading-relaxed text-navy-700">{analysis.summary}</p>

        {findings.length === 0 ? (
          <p className="text-sm text-navy-500">
            No specific findings were reported for this stage.
          </p>
        ) : (
          <div className="space-y-3">
            {findings.map((finding, index) => (
              <FindingCard
                key={`${finding.title}-${index}`}
                finding={finding}
                citations={citations}
              />
            ))}
          </div>
        )}

        <Caveats analysis={analysis} />
      </CardBody>
    </Card>
  )
}

/**
 * Assumptions and evidence gaps are shown alongside every stage, not
 * hidden in a footnote. The workflow is explicitly designed to report what
 * it could not establish, and burying that would undo the point of it.
 */
export function Caveats({ analysis }: { analysis: BusinessAnalysisResult }) {
  const hasAssumptions = analysis.assumptions.length > 0
  const hasGaps = analysis.insufficient_evidence.length > 0
  if (!hasAssumptions && !hasGaps) return null

  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      {hasAssumptions ? (
        <div className="rounded-lg border border-navy-200 bg-navy-50/60 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-navy-600">
            Assumptions made
          </p>
          <ul className="mt-2 space-y-2">
            {analysis.assumptions.map((assumption, index) => (
              <li key={index} className="text-sm leading-relaxed text-navy-700">
                <span className="font-medium">{assumption.description}</span>
                <span className="text-navy-500"> — {assumption.reason}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {hasGaps ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50/70 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">
            Not established by your documents
          </p>
          <ul className="mt-2 list-disc space-y-1 pl-4">
            {analysis.insufficient_evidence.map((gap, index) => (
              <li key={index} className="text-sm leading-relaxed text-amber-900">
                {gap}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}
