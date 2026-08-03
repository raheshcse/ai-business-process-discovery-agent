/**
 * The single place the frontend talks to HTTP.
 *
 * Two things matter here. First, every failure becomes an `ApiError` with a
 * message a person can act on -- FastAPI's `detail` may be a string or a
 * list of validation objects, and neither renders usefully on its own.
 * Second, nothing here knows about React, so it stays testable and reusable.
 */

import { API_BASE_URL } from './config'

export class ApiError extends Error {
  readonly status: number
  readonly detail: unknown

  constructor(message: string, status: number, detail?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }

  /** True for causes the user can fix by changing their input. */
  get isValidation(): boolean {
    return this.status === 422 || this.status === 400
  }

  get isNotFound(): boolean {
    return this.status === 404
  }

  /** True when the backend could not be reached at all. */
  get isNetwork(): boolean {
    return this.status === 0
  }
}

interface ValidationDetail {
  loc?: (string | number)[]
  msg?: string
}

function formatDetail(detail: unknown, fallback: string): string {
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const messages = (detail as ValidationDetail[])
      .map((item) => {
        const field = item.loc?.filter((part) => part !== 'body').join('.')
        return field && item.msg ? `${field}: ${item.msg}` : item.msg
      })
      .filter(Boolean)
    if (messages.length) return messages.join('; ')
  }
  return fallback
}

const STATUS_FALLBACKS: Record<number, string> = {
  400: 'The request was rejected. Please check the values you entered.',
  404: 'That item no longer exists. It may have been deleted.',
  409: 'This action conflicts with the current state of the project.',
  413: 'That file is too large.',
  422: 'Some values are invalid. Please review the form.',
  500: 'The server hit an unexpected error. Please try again.',
  502: 'The server is unreachable. Check that the backend is running.',
  503: 'The server is temporarily unavailable. Please try again shortly.',
}

async function toApiError(response: Response): Promise<ApiError> {
  const fallback =
    STATUS_FALLBACKS[response.status] ??
    `Request failed with status ${response.status}.`
  let detail: unknown
  try {
    detail = (await response.json())?.detail
  } catch {
    detail = undefined
  }
  return new ApiError(formatDetail(detail, fallback), response.status, detail)
}

interface RequestOptions {
  method?: string
  body?: unknown
  signal?: AbortSignal
}

async function send<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, signal } = options

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      signal,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(
      `Could not reach the API at ${API_BASE_URL}. Check that the backend is running and that VITE_API_BASE_URL is correct.`,
      0,
      error,
    )
  }

  if (!response.ok) throw await toApiError(response)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  get: <T>(path: string, signal?: AbortSignal) => send<T>(path, { signal }),
  post: <T>(path: string, body?: unknown) => send<T>(path, { method: 'POST', body }),
  put: <T>(path: string, body: unknown) => send<T>(path, { method: 'PUT', body }),
  delete: (path: string) => send<void>(path, { method: 'DELETE' }),
}

/**
 * Uploads use XMLHttpRequest rather than fetch purely because `fetch` cannot
 * report upload progress, and a 25 MB PDF with no progress bar feels broken.
 */
export function uploadFile<T>(
  path: string,
  file: File,
  onProgress?: (percent: number) => void,
): { promise: Promise<T>; abort: () => void } {
  const request = new XMLHttpRequest()
  const promise = new Promise<T>((resolve, reject) => {
    request.open('POST', `${API_BASE_URL}${path}`)

    request.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    }

    request.onload = () => {
      const status = request.status
      if (status >= 200 && status < 300) {
        onProgress?.(100)
        try {
          resolve(JSON.parse(request.responseText) as T)
        } catch {
          reject(new ApiError('The server returned a malformed response.', status))
        }
        return
      }
      let detail: unknown
      try {
        detail = JSON.parse(request.responseText)?.detail
      } catch {
        detail = undefined
      }
      reject(
        new ApiError(
          formatDetail(
            detail,
            STATUS_FALLBACKS[status] ?? `Upload failed with status ${status}.`,
          ),
          status,
          detail,
        ),
      )
    }

    request.onerror = () =>
      reject(
        new ApiError(
          `Could not reach the API at ${API_BASE_URL}. Check that the backend is running.`,
          0,
        ),
      )
    request.onabort = () => reject(new ApiError('Upload cancelled.', 0))

    const form = new FormData()
    form.append('file', file)
    request.send(form)
  })

  return { promise, abort: () => request.abort() }
}
