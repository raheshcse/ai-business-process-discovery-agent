import { useHealth } from '@/hooks/queries'

/**
 * Surfaces the one configuration problem that silently breaks analyses.
 *
 * With the non-semantic `local` embedding provider, retrieval scores are
 * effectively random and often negative, so the evidence governance gate
 * blocks runs for reasons that have nothing to do with the documents. That
 * looks like a document problem to a user, so it needs saying out loud.
 */
export function EnvironmentBanner() {
  const { data: health } = useHealth()
  if (!health) return null

  // A missing or unreachable model stops everything, so it outranks the
  // embedding-quality warning below.
  if (health.provider_error) {
    return (
      <div className="sticky bottom-0 z-30 border-t border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900 sm:px-6 lg:px-8">
        <p className="font-semibold">
          {health.provider_reachable
            ? 'A required model is not installed'
            : 'The model provider is not reachable'}
        </p>
        <p className="mt-0.5 leading-relaxed">{health.provider_error}</p>
      </div>
    )
  }

  if (health.embeddings_are_semantic) return null

  return (
    <div className="sticky bottom-0 z-30 border-t border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 sm:px-6 lg:px-8">
      <p className="font-semibold">
        Retrieval is running without semantic embeddings
      </p>
      <p className="mt-0.5 leading-relaxed">
        <code className="rounded bg-amber-100 px-1">
          EMBEDDING_PROVIDER={health.embedding_provider}
        </code>{' '}
        scores document relevance by hashing rather than meaning, so analyses
        may be stopped at the evidence gate regardless of what your documents
        contain. Set <code className="rounded bg-amber-100 px-1">EMBEDDING_PROVIDER=ollama</code>{' '}
        and pull an embedding model for meaningful results.
      </p>
    </div>
  )
}
