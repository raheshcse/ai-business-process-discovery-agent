import { useCallback, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { documentsApi } from '@/api/endpoints'
import { ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE_BYTES } from '@/api/config'
import { Button } from '@/components/ui/Button'
import { Banner } from '@/components/ui/States'
import { UploadIcon } from '@/components/ui/icons'
import { queryKeys } from '@/hooks/queries'
import { cn } from '@/lib/cn'
import { formatBytes } from '@/lib/format'
import { validateFile } from './validateFile'

interface UploadItem {
  id: string
  name: string
  size: number
  percent: number
  state: 'uploading' | 'done' | 'error'
  message?: string
}

export function UploadArea({ projectId }: { projectId: string }) {
  const client = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [items, setItems] = useState<UploadItem[]>([])

  const patch = (id: string, changes: Partial<UploadItem>) =>
    setItems((current) =>
      current.map((item) => (item.id === id ? { ...item, ...changes } : item)),
    )

  const upload = useCallback(
    async (files: File[]) => {
      for (const file of files) {
        const id = `${file.name}-${Date.now()}-${Math.random()}`
        const rejection = validateFile(file)

        if (rejection) {
          setItems((current) => [
            ...current,
            {
              id,
              name: file.name,
              size: file.size,
              percent: 0,
              state: 'error',
              message: rejection,
            },
          ])
          continue
        }

        setItems((current) => [
          ...current,
          { id, name: file.name, size: file.size, percent: 0, state: 'uploading' },
        ])

        try {
          const { promise } = documentsApi.upload(projectId, file, (percent) =>
            patch(id, { percent }),
          )
          await promise
          patch(id, { state: 'done', percent: 100 })
          void client.invalidateQueries({ queryKey: queryKeys.documents(projectId) })
          void client.invalidateQueries({ queryKey: queryKeys.dashboard })
        } catch (error) {
          patch(id, {
            state: 'error',
            message: error instanceof Error ? error.message : 'Upload failed.',
          })
        }
      }
    },
    [client, projectId],
  )

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault()
    setDragging(false)
    void upload(Array.from(event.dataTransfer.files))
  }

  const active = items.filter((item) => item.state !== 'done')

  return (
    <div className="space-y-3">
      <div
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={cn(
          'rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors',
          dragging
            ? 'border-accent-500 bg-accent-500/5'
            : 'border-navy-200 bg-navy-50/40 hover:border-navy-300',
        )}
      >
        <div className="mx-auto grid h-11 w-11 place-items-center rounded-lg bg-white text-accent-500 shadow-card">
          <UploadIcon />
        </div>
        <p className="mt-3 text-sm font-medium text-navy-900">
          Drop process documentation here
        </p>
        <p className="mt-1 text-xs text-navy-500">
          {ALLOWED_EXTENSIONS.join(', ')} · up to {formatBytes(MAX_UPLOAD_SIZE_BYTES)} each
        </p>
        <div className="mt-4">
          <Button variant="secondary" size="sm" onClick={() => inputRef.current?.click()}>
            Choose files
          </Button>
        </div>
        <input
          ref={inputRef}
          type="file"
          multiple
          className="sr-only"
          accept={ALLOWED_EXTENSIONS.join(',')}
          aria-label="Choose documents to upload"
          onChange={(event) => {
            void upload(Array.from(event.target.files ?? []))
            event.target.value = ''
          }}
        />
      </div>

      {active.length > 0 ? (
        <ul className="space-y-2">
          {active.map((item) => (
            <li key={item.id} className="card px-4 py-3">
              <div className="flex items-center justify-between gap-3">
                <p className="min-w-0 truncate text-sm font-medium text-navy-900">
                  {item.name}
                </p>
                <span className="shrink-0 text-xs text-navy-500">
                  {item.state === 'uploading'
                    ? `${item.percent}%`
                    : formatBytes(item.size)}
                </span>
              </div>
              {item.state === 'uploading' ? (
                <div
                  className="mt-2 h-1.5 overflow-hidden rounded-full bg-navy-100"
                  role="progressbar"
                  aria-valuenow={item.percent}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label={`Uploading ${item.name}`}
                >
                  <div
                    className="h-full rounded-full bg-accent-500 transition-[width] duration-200"
                    style={{ width: `${item.percent}%` }}
                  />
                </div>
              ) : null}
              {item.state === 'error' ? (
                <div className="mt-2">
                  <Banner tone="danger" title="Upload rejected">
                    {item.message}
                  </Banner>
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
