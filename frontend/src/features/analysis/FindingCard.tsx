import { Chip, SeverityChip } from '@/components/ui/StatusChip'
import { humanise } from '@/lib/format'
import type { AnalysisFinding, Citation } from '@/types/api'

/**
 * Renders one finding with its evidence.
 *
 * Every claim the model makes cites `Source N` markers. Resolving those
 * back to real filenames is the difference between "the AI said so" and
 * something a business reader can check.
 */
export function FindingCard({
  finding,
  citations,
}: {
  finding: AnalysisFinding
  citations: Citation[]
}) {
  const byId = new Map(citations.map((citation) => [citation.source_id, citation]))

  return (
    <article className="card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h4 className="min-w-0 text-sm font-semibold text-navy-900">{finding.title}</h4>
        <div className="flex shrink-0 items-center gap-2">
          <Chip tone="neutral">{humanise(finding.category)}</Chip>
          <SeverityChip severity={finding.severity} />
        </div>
      </div>

      <p className="mt-2.5 text-sm leading-relaxed text-navy-700">
        {finding.description}
      </p>

      <div className="mt-4 rounded-lg border-l-2 border-accent-500 bg-accent-500/5 px-4 py-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-accent-700">
          Recommended action
        </p>
        <p className="mt-1 text-sm leading-relaxed text-navy-800">
          {finding.recommendation}
        </p>
      </div>

      <footer className="mt-3.5 flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-navy-500">Evidence:</span>
        {finding.evidence_source_ids.length === 0 ? (
          <span className="text-xs text-amber-700">No source cited</span>
        ) : (
          finding.evidence_source_ids.map((sourceId) => {
            const citation = byId.get(sourceId)
            return (
              <span
                key={sourceId}
                className="inline-flex items-center gap-1.5 rounded-md bg-navy-100 px-2 py-1 text-xs text-navy-700"
                title={
                  citation
                    ? `Relevance ${citation.score.toFixed(3)} · section ${citation.chunk_index + 1}`
                    : 'This source is not in the retrieved evidence.'
                }
              >
                <span className="font-semibold">{sourceId}</span>
                {citation ? (
                  <span className="text-navy-500">
                    {citation.filename ?? citation.document_id.slice(0, 8)}
                  </span>
                ) : (
                  <span className="text-amber-700">unresolved</span>
                )}
              </span>
            )
          })
        )}
      </footer>
    </article>
  )
}
