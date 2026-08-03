import { Chip } from '@/components/ui/StatusChip'
import { humanise } from '@/lib/format'
import type { AnalysisFinding, Citation } from '@/types/api'

/**
 * A readable walk through the discovered process.
 *
 * The backend returns findings, not a formal step graph -- there is no
 * `owner`, `input` or `dependency` field on `AnalysisFinding`. Rather than
 * invent a BPMN diagram from data that cannot support one, this presents
 * the discovered elements in order, grouped by what they describe, and
 * labels each with the role it plays. Nothing here is fabricated.
 */
export function ProcessFlow({
  findings,
  citations,
}: {
  findings: AnalysisFinding[]
  citations: Citation[]
}) {
  const byId = new Map(citations.map((citation) => [citation.source_id, citation]))

  if (findings.length === 0) {
    return (
      <p className="text-sm text-navy-500">
        No process elements were identified from the supplied documents.
      </p>
    )
  }

  return (
    <ol className="relative space-y-0">
      {findings.map((finding, index) => (
        <li key={`${finding.title}-${index}`} className="relative flex gap-4 pb-6 last:pb-0">
          {/* Connector */}
          {index < findings.length - 1 ? (
            <span
              className="absolute left-[15px] top-9 h-[calc(100%-1.5rem)] w-px bg-navy-200"
              aria-hidden="true"
            />
          ) : null}

          <span className="relative z-10 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-navy-900 text-xs font-semibold text-white">
            {index + 1}
          </span>

          <div className="min-w-0 flex-1 pt-0.5">
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="text-sm font-semibold text-navy-900">{finding.title}</h4>
              <Chip tone="neutral">{humanise(finding.category)}</Chip>
            </div>
            <p className="mt-1.5 text-sm leading-relaxed text-navy-700">
              {finding.description}
            </p>
            <p className="mt-2 text-sm leading-relaxed text-navy-600">
              <span className="font-medium text-navy-800">Next: </span>
              {finding.recommendation}
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {finding.evidence_source_ids.map((sourceId) => {
                const citation = byId.get(sourceId)
                return (
                  <span
                    key={sourceId}
                    className="rounded bg-navy-100 px-1.5 py-0.5 text-[11px] text-navy-600"
                  >
                    {sourceId}
                    {citation?.filename ? ` · ${citation.filename}` : ''}
                  </span>
                )
              })}
            </div>
          </div>
        </li>
      ))}
    </ol>
  )
}
