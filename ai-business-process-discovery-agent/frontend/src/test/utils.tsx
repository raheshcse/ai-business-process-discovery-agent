import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, type RenderOptions } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import type { ReactElement, ReactNode } from 'react'
import { AppLayout } from '@/components/layout/AppLayout'

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
      mutations: { retry: false },
    },
  })
}

/**
 * Renders a page inside the real layout and router.
 *
 * Pages read `useOutletContext`, so mounting them bare would throw. Going
 * through `AppLayout` also means the tests exercise the same tree the app
 * ships.
 */
export function renderPage(
  ui: ReactElement,
  { route = '/', path = '/', ...options }: { route?: string; path?: string } & Omit<
    RenderOptions,
    'wrapper'
  > = {},
) {
  const client = createTestQueryClient()

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[route]}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path={path} element={children} />
              <Route path="*" element={<div>navigated away</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    )
  }

  return { client, ...render(ui, { wrapper: Wrapper, ...options }) }
}
