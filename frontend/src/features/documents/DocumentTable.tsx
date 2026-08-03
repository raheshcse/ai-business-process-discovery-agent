import { Button } from '@/components/ui/Button'
import { IndexStatusChip } from '@/components/ui/StatusChip'
import { Table, Td, Th } from '@/components/ui/Table'
import { EmptyState } from '@/components/ui/States'
import { DocumentIcon, TrashIcon } from '@/components/ui/icons'
import { useDeleteDocument, useReindexDocument } from '@/hooks/queries'
import { formatBytes, formatRelative } from '@/lib/format'
import type { ProjectDocument } from '@/types/api'

export function DocumentTable({
  projectId,
  documents,
}: {
  projectId: string
  documents: ProjectDocument[]
}) {
  const removeDocument = useDeleteDocument(projectId)
  const reindexDocument = useReindexDocument(projectId)

  if (documents.length === 0) {
    return (
      <EmptyState
        icon={<DocumentIcon className="h-10 w-10" />}
        title="No documents yet"
        description="Upload process maps, SOPs, policy documents, spreadsheets or meeting notes. Each one is text-extracted and indexed so the analysis can cite it."
      />
    )
  }

  return (
    <Table
      head={
        <tr>
          <Th>Document</Th>
          <Th>Status</Th>
          <Th className="hidden lg:table-cell">Extracted</Th>
          <Th className="hidden sm:table-cell">Uploaded</Th>
          <Th className="text-right">Actions</Th>
        </tr>
      }
    >
      {documents.map((document) => (
        <tr key={document.id} className="align-top hover:bg-navy-50/60">
          <Td>
            <p className="font-medium text-navy-900">{document.original_filename}</p>
            <p className="mt-0.5 text-xs text-navy-500">
              {formatBytes(document.size_bytes)} · {document.file_extension.slice(1).toUpperCase()}
            </p>
            {document.index_status === 'failed' && document.index_error ? (
              <p className="mt-1.5 rounded-md bg-red-50 px-2 py-1 text-xs text-red-800">
                {document.index_error}
              </p>
            ) : null}
          </Td>
          <Td>
            <IndexStatusChip status={document.index_status} />
          </Td>
          <Td className="hidden text-xs text-navy-600 lg:table-cell">
            {document.index_status === 'indexed' ? (
              <>
                <div>{document.word_count?.toLocaleString() ?? '—'} words</div>
                <div className="text-navy-400">
                  {document.chunk_count ?? 0} searchable section
                  {document.chunk_count === 1 ? '' : 's'}
                  {document.page_count ? ` · ${document.page_count} pages` : ''}
                </div>
              </>
            ) : (
              '—'
            )}
          </Td>
          <Td className="hidden whitespace-nowrap text-navy-500 sm:table-cell">
            {formatRelative(document.created_at)}
          </Td>
          <Td>
            <div className="flex items-center justify-end gap-1">
              {document.index_status === 'failed' ? (
                <Button
                  variant="secondary"
                  size="sm"
                  loading={
                    reindexDocument.isPending &&
                    reindexDocument.variables === document.id
                  }
                  onClick={() => reindexDocument.mutate(document.id)}
                >
                  Retry
                </Button>
              ) : null}
              <Button
                variant="ghost"
                size="sm"
                aria-label={`Delete ${document.original_filename}`}
                className="text-red-600 hover:bg-red-50"
                loading={
                  removeDocument.isPending && removeDocument.variables === document.id
                }
                onClick={() => removeDocument.mutate(document.id)}
              >
                <TrashIcon className="h-4 w-4" />
              </Button>
            </div>
          </Td>
        </tr>
      ))}
    </Table>
  )
}
