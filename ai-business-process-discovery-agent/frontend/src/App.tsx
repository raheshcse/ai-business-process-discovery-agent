import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { AppRoutes } from './routes'
import { ApiError } from './api/client'

/**
 * Retrying a 404 or a validation failure just delays the error the user
 * needs to see, so only transient failures are retried.
 */
export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: (failureCount, error) => {
          if (error instanceof ApiError && (error.isNotFound || error.isValidation)) {
            return false
          }
          return failureCount < 2
        },
        refetchOnWindowFocus: false,
        staleTime: 5_000,
      },
      mutations: { retry: false },
    },
  })
}

export function App() {
  const [client] = [createQueryClient()]
  return (
    <QueryClientProvider client={client}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
