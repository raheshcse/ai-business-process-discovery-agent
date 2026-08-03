import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { Banner, InlineError } from '@/components/ui/States'
import { SparkIcon } from '@/components/ui/icons'
import { useStartAnalysis } from '@/hooks/queries'
import { cn } from '@/lib/cn'
import type { ProjectDocument } from '@/types/api'

const SUGGESTIONS = [
  'How does this process work end to end, and who owns each step?',
  'Where does this process slow down, and why?',
  'What operational and control risks does this process carry?',
  'Which steps could be automated, and which must stay human?',
]

export function StartAnalysisPanel({
  projectId,
  documents,
}: {
  projectId: string
  documents: ProjectDocument[]
}) {
  const navigate = useNavigate()
  const startAnalysis = useStartAnalysis(projectId)
  const [question, setQuestion] = useState('')
  const [selected, setSelected] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  const indexed = documents.filter((document) => document.index_status === 'indexed')
  const stillProcessing = documents.some(
    (document) =>
      document.index_status === 'pending' || document.index_status === 'processing',
  )
  const canRun = indexed.length > 0 && !startAnalysis.isPending

  const toggle = (documentId: string) =>
    setSelected((current) =>
      current.includes(documentId)
        ? current.filter((id) => id !== documentId)
        : [...current, documentId],
    )

  const submit = () => {
    const trimmed = question.trim()
    if (trimmed.length < 5) {
      setError('Ask a question of at least five characters.')
      return
    }
    if (trimmed.length > 2000) {
      setError('That question is too long. Keep it under 2000 characters.')
      return
    }
    setError(null)
    startAnalysis.mutate(
      {
        question: trimmed,
        document_id_filters: selected.length > 0 ? selected : undefined,
      },
      { onSuccess: (run) => navigate(`/analyses/${run.id}`) },
    )
  }

  if (indexed.length === 0) {
    return (
      <Banner
        tone={stillProcessing ? 'info' : 'warning'}
        title={
          stillProcessing
            ? 'Preparing your documents'
            : 'No usable evidence yet'
        }
      >
        {stillProcessing
          ? 'Text extraction and indexing are still running. The analysis button unlocks as soon as at least one document is ready.'
          : 'Upload at least one document that can be read successfully. The analysis only makes claims it can trace to your evidence, so it will not run without any.'}
      </Banner>
    )
  }

  return (
    <div className="space-y-4">
      {startAnalysis.isError ? (
        <Banner tone="danger" title="Could not start the analysis">
          {(startAnalysis.error as Error).message}
        </Banner>
      ) : null}

      <div>
        <label className="label" htmlFor="analysis-question">
          What do you want to understand?
        </label>
        <textarea
          id="analysis-question"
          rows={3}
          className={cn('input mt-1.5 resize-y', error && 'input-invalid')}
          placeholder="How does the invoice approval process work end to end?"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          aria-invalid={Boolean(error)}
        />
        {error ? <InlineError>{error}</InlineError> : null}
        <div className="mt-2 flex flex-wrap gap-1.5">
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => {
                setQuestion(suggestion)
                setError(null)
              }}
              className="rounded-full border border-navy-200 px-3 py-1 text-xs text-navy-600 transition-colors hover:border-accent-400 hover:text-accent-600"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>

      {indexed.length > 1 ? (
        <fieldset>
          <legend className="label">
            Limit to specific documents{' '}
            <span className="font-normal text-navy-500">(optional)</span>
          </legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {indexed.map((document) => {
              const checked = selected.includes(document.id)
              return (
                <label
                  key={document.id}
                  className={cn(
                    'inline-flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-1.5 text-xs transition-colors',
                    checked
                      ? 'border-accent-500 bg-accent-500/10 text-accent-700'
                      : 'border-navy-200 text-navy-600 hover:border-navy-300',
                  )}
                >
                  <input
                    type="checkbox"
                    className="sr-only"
                    checked={checked}
                    onChange={() => toggle(document.id)}
                  />
                  {document.original_filename}
                </label>
              )
            })}
          </div>
          <p className="mt-2 text-xs text-navy-500">
            Leave all unselected to search every indexed document in this project.
          </p>
        </fieldset>
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        <Button
          icon={<SparkIcon className="h-4 w-4" />}
          disabled={!canRun}
          loading={startAnalysis.isPending}
          onClick={submit}
        >
          Run governed analysis
        </Button>
        <p className="text-xs text-navy-500">
          Searches {selected.length || indexed.length} document
          {(selected.length || indexed.length) === 1 ? '' : 's'} · five analysis stages,
          eleven governance checks
        </p>
      </div>
    </div>
  )
}
