import { afterEach, describe, expect, it, vi } from 'vitest'
import { screen, within } from '@testing-library/react'
import { AnalysisResultsPage } from '../AnalysisResultsPage'
import { renderPage } from '@/test/utils'
import { mockApi } from '@/test/server'
import { blockedRun, completedRun, health } from '@/test/fixtures'

afterEach(() => vi.unstubAllGlobals())

const render = () =>
  renderPage(<AnalysisResultsPage />, {
    route: '/analyses/run-1',
    path: '/analyses/:runId',
  })

describe('Analysis results', () => {
  it('leads with the executive summary', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      { match: /\/analyses\/run-1$/, body: completedRun },
    ])

    render()

    expect(await screen.findByText('Executive summary')).toBeInTheDocument()
    expect(
      screen.getByText(/largest delay at manager approval/),
    ).toBeInTheDocument()
  })

  it('shows every analysis section with its findings', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      { match: /\/analyses\/run-1$/, body: completedRun },
    ])

    render()

    // Headings, not the stat-card labels that reuse the same words.
    expect(
      await screen.findByRole('heading', { name: 'Business process' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Bottlenecks' })).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Risks and controls' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Automation opportunities' }),
    ).toBeInTheDocument()

    expect(screen.getByText('Manual invoice entry')).toBeInTheDocument()
    expect(screen.getByText('Approval sits three to five days')).toBeInTheDocument()
    expect(screen.getByText('Automate invoice capture')).toBeInTheDocument()
  })

  it('orders risks by severity, most serious first', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      { match: /\/analyses\/run-1$/, body: completedRun },
    ])

    render()

    await screen.findByText('Risks and controls')
    const titles = screen
      .getAllByRole('article')
      .map((article) => within(article).getAllByRole('heading')[0].textContent)

    const critical = titles.indexOf('Transcription errors are uncontrolled')
    const low = titles.indexOf('Approval evidence is in email')
    expect(critical).toBeLessThan(low)
  })

  it('resolves every citation marker to a real filename', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      { match: /\/analyses\/run-1$/, body: completedRun },
    ])

    render()

    await screen.findByText('Source documents')
    expect(screen.queryByText('unresolved')).not.toBeInTheDocument()
    expect(screen.getAllByText('invoice-process.pdf').length).toBeGreaterThan(0)
  })

  it('reports what your documents could not establish', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      { match: /\/analyses\/run-1$/, body: completedRun },
    ])

    render()

    expect(
      await screen.findByText('Invoice volumes per month'),
    ).toBeInTheDocument()
  })

  it('explains a governance stop without calling it a failure', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      { match: /\/analyses\/run-1$/, body: blockedRun },
    ])

    render()

    expect(
      await screen.findByText('A governance gate stopped this analysis'),
    ).toBeInTheDocument()
    expect(screen.getByText('UNSUPPORTED_FINDINGS')).toBeInTheDocument()
    // Partial results are still shown rather than discarded.
    expect(screen.getByText('Partial results')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'See why' })).toHaveAttribute(
      'href',
      '/analyses/run-2/governance',
    )
  })

  it('shows live stage progress while a run is still going', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      {
        match: /\/analyses\/run-1$/,
        body: { ...completedRun, status: 'running', current_stage: 'risk_analysis' },
      },
    ])

    render()

    expect(await screen.findByText('Analysis in progress')).toBeInTheDocument()
    expect(screen.getByText('Analysing risks')).toBeInTheDocument()
  })
})
