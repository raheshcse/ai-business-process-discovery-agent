/**
 * A tiny `fetch` stub keyed by URL suffix.
 *
 * MSW would be the usual choice, but it is a large dependency for what
 * these tests need, and routing on the path suffix keeps each test's
 * intent visible in one place.
 */

import { vi } from 'vitest'

export interface Route {
  match: RegExp
  method?: string
  status?: number
  body?: unknown
  /** Throw a network-level failure rather than an HTTP error. */
  networkError?: boolean
}

export function mockApi(routes: Route[]) {
  const calls: { url: string; method: string; body?: unknown }[] = []

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString()
    const method = (init?.method ?? 'GET').toUpperCase()
    calls.push({
      url,
      method,
      body: init?.body ? JSON.parse(init.body as string) : undefined,
    })

    const route = routes.find(
      (candidate) =>
        candidate.match.test(url) && (candidate.method ?? 'GET').toUpperCase() === method,
    )

    if (!route) {
      return new Response(JSON.stringify({ detail: `No stub for ${method} ${url}` }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      })
    }
    if (route.networkError) throw new TypeError('Failed to fetch')

    const status = route.status ?? 200
    if (status === 204) return new Response(null, { status })
    return new Response(JSON.stringify(route.body ?? {}), {
      status,
      headers: { 'Content-Type': 'application/json' },
    })
  })

  vi.stubGlobal('fetch', fetchMock)
  return { calls, fetchMock }
}
