import { afterEach, describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { DashboardPage } from '../DashboardPage'
import { renderPage } from '@/test/utils'
import { mockApi } from '@/test/server'
import { dashboard, health } from '@/test/fixtures'

afterEach(() => vi.unstubAllGlobals())

describe('Dashboard', () => {
  it('shows portfolio totals from the API', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      { match: /\/dashboard$/, body: dashboard },
    ])

    renderPage(<DashboardPage />)

    expect(await screen.findByText('Projects')).toBeInTheDocument()
    expect(await screen.findByText('4/5')).toBeInTheDocument()
    expect(await screen.findByText('1 critical · 1 high · 2 medium')).toBeInTheDocument()
    expect(await screen.findByText('2 bottlenecks found')).toBeInTheDocument()
  })

  it('links recent activity to the analysis it came from', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      { match: /\/dashboard$/, body: dashboard },
    ])

    renderPage(<DashboardPage />)

    const link = await screen.findByRole('link', {
      name: /How does the invoice approval process work/,
    })
    expect(link).toHaveAttribute('href', '/analyses/run-1')
  })

  it('invites the user to start when there are no projects', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      {
        match: /\/dashboard$/,
        body: { ...dashboard, project_count: 0, recent_activity: [] },
      },
    ])

    renderPage(<DashboardPage />)

    expect(await screen.findByText('Nothing to show yet')).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: /Create your first project/ }),
    ).toBeInTheDocument()
  })

  it('explains a network failure instead of showing an empty page', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      { match: /\/dashboard$/, networkError: true },
    ])

    renderPage(<DashboardPage />)

    expect(await screen.findByText('Cannot reach the server')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })
})
