/** Environment-based API configuration. No URL is hardcoded in a component. */

const DEFAULT_BASE_URL = 'http://localhost:8000/api/v1'
const DEFAULT_POLL_INTERVAL_MS = 2000

function readNumber(value: string | undefined, fallback: number): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback
}

/** Trailing slashes would produce `//projects` when joined with a path. */
export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? DEFAULT_BASE_URL
).replace(/\/+$/, '')

export const POLL_INTERVAL_MS = readNumber(
  import.meta.env.VITE_POLL_INTERVAL_MS,
  DEFAULT_POLL_INTERVAL_MS,
)

export const MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024

/** Mirrors `ALLOWED_CONTENT_TYPES` in `app/services/document_service.py`. */
export const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt', '.csv', '.xlsx'] as const
