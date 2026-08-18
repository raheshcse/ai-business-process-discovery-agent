import { afterEach, describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { PageShell } from '../PageShell'
import { renderPage } from '@/test/utils'
import { mockApi } from '@/test/server'
import { health } from '@/test/fixtures'

afterEach(() => vi.unstubAllGlobals())

const render = () =>
  renderPage(
    <PageShell title="Dashboard">
      <div />
    </PageShell>,
  )

describe('Provider badge', () => {
  it('is green only when the provider answered and has its models', async () => {
    mockApi([{ match: /\/health$/, body: health }])
    render()
    expect(await screen.findByText('ollama · llama3.2')).toBeInTheDocument()
  })

  it('warns when a configured model is not installed', async () => {
    mockApi([
      {
        match: /\/health$/,
        body: {
          ...health,
          status: 'degraded',
          llm_model_available: false,
          provider_error:
            'Ollama is running but these models are not installed: llama3.2. ' +
            'Install with: ollama pull llama3.2',
        },
      },
    ])
    render()

    expect(await screen.findByText('Model not installed')).toBeInTheDocument()
    expect(screen.queryByText('ollama · llama3.2')).not.toBeInTheDocument()
    expect(screen.getByText(/ollama pull llama3.2/)).toBeInTheDocument()
  })

  it('reports an unreachable provider distinctly from a missing model', async () => {
    mockApi([
      {
        match: /\/health$/,
        body: {
          ...health,
          status: 'degraded',
          provider_reachable: false,
          llm_model_available: false,
          embedding_model_available: false,
          provider_error:
            'Cannot reach Ollama at http://localhost:11434. Start it with: ollama serve',
        },
      },
    ])
    render()

    expect(await screen.findByText('ollama unreachable')).toBeInTheDocument()
    expect(screen.getByText(/ollama serve/)).toBeInTheDocument()
  })

  it('says the backend is unreachable when health itself fails', async () => {
    mockApi([{ match: /\/health$/, networkError: true }])
    render()
    expect(await screen.findByText('Backend unreachable')).toBeInTheDocument()
  })
})
